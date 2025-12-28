# Architecture Deep Dive

This document explains the engineering decisions behind achieving **650k+ requests/minute** with **100% reliability** on commodity hardware.

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Binary Protocol Design](#2-binary-protocol-design)
3. [Concurrency Model](#3-concurrency-model)
4. [State Management & Atomicity](#4-state-management--atomicity)
5. [Performance Bottlenecks & Solutions](#5-performance-bottlenecks--solutions)
6. [Trade-offs & Future Work](#6-trade-offs--future-work)

---

## 1. System Overview

### Architecture Diagram
```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │◄───────►│  TCP Server  │◄───────►│    Redis    │
│ (Goroutine) │  Binary │  (Goroutine  │   Lua   │  (Atomic    │
│             │  TLV    │   per conn)  │  Script │   State)    │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │   Channel    │
                        │   Buffer     │
                        │  (5k slots)  │
                        └──────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │   Manager    │
                        │  Goroutine   │
                        └──────────────┘
```

### Key Metrics
- **Throughput**: 650,209 RPM (10,836 RPS)
- **Latency**: Sub-millisecond avg, <10ms p99
- **Concurrency**: 1,000 simultaneous connections
- **Success Rate**: 100.00% under burst load
- **Memory**: ~2MB for 1,000 goroutines (2KB each)

---

## 2. Binary Protocol Design

### Problem: Text Protocol Overhead

Text-based protocols (HTTP, WebSockets, JSON-over-TCP) introduce multiple sources of latency:

**Parsing Overhead:**
- Must scan byte-by-byte for delimiters (`\r\n`, `}`)
- Allocates temporary buffers for string operations
- JSON unmarshaling involves reflection and type checking

**Framing Ambiguity:**
- "Where does message 1 end and message 2 begin?"
- Requires buffering partial messages
- Edge cases: split delimiters, escaped characters

**Bandwidth:**
```json
// Text: 89 bytes
{"type":"BID","auction_id":12345,"user_id":67890,"amount":150.50}

// Binary TLV: 22 bytes (4x smaller)
[type:1][len:16][auction_id:4][user_id:4][amount:8]
```

### Solution: Type-Length-Value (TLV) Framing

**Wire Format:**
```
┌──────┬──────┬─────────────────┐
│ Type │ Len  │     Payload     │
│  1B  │  1B  │  Len bytes      │
└──────┴──────┴─────────────────┘
```

**Implementation:**
```go
type Frame struct {
    Type    uint8  // 1 = BID, 2 = RESULT, 3 = ERROR
    Length  uint8  // Payload size (max 255 bytes)
    Payload []byte
}

func (f *Frame) Write(conn net.Conn) error {
    header := []byte{f.Type, f.Length}
    if _, err := conn.Write(header); err != nil {
        return err
    }
    _, err := conn.Write(f.Payload)
    return err
}

func ReadFrame(conn net.Conn) (*Frame, error) {
    header := make([]byte, 2)
    if _, err := io.ReadFull(conn, header); err != nil {
        return nil, err
    }
    
    payload := make([]byte, header[1])
    if _, err := io.ReadFull(conn, payload); err != nil {
        return nil, err
    }
    
    return &Frame{
        Type:    header[0],
        Length:  header[1],
        Payload: payload,
    }, nil
}
```

**Benefits:**
- **Zero-copy parsing**: `io.ReadFull()` reads directly into pre-allocated buffer
- **No partial frames**: Fixed header guarantees we know payload size upfront
- **Deterministic memory**: Max frame size = 257 bytes (2-byte header + 255-byte payload)

**Trade-offs:**
- ❌ Not human-readable (can't `telnet` to debug)
- ❌ No browser compatibility (WebSockets needed for web clients)
- ✅ Acceptable for server-to-server / benchmarking use case

---

## 3. Concurrency Model

### The Python Baseline

**Original Architecture (Python + asyncio):**
```python
import selectors
import socket

sel = selectors.DefaultSelector()

def accept(sock):
    conn, addr = sock.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, read)

def read(conn):
    data = conn.recv(1024)
    process_bid(data)  # <-- GIL BOTTLENECK

sock = socket.socket()
sock.bind(('', 8080))
sock.listen()
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, accept)

while True:
    events = sel.select()  # OS wakes us when I/O ready
    for key, mask in events:
        callback = key.data
        callback(key.fileobj)
```

**The Problem: Python's Global Interpreter Lock (GIL)**

The GIL allows only one thread to execute Python bytecode at a time:
- ✅ **I/O operations** (reading sockets) release the GIL → parallelism OK
- ❌ **CPU operations** (parsing bids, encoding JSON) hold the GIL → single-threaded

**Impact on this workload:**
```
18-core CPU, 1000 bids/sec incoming:
  - 80% time in recv() → 18 cores utilized
  - 20% time in process_bid() → 1 core utilized
  
Effective CPU usage: ~20% (wasting 17 cores)
```

**Result:** Peaked at **150k RPM** with 92% success rate under load.

---

### The Go Rewrite

**Architecture: Goroutine-per-Connection**
```go
func handleClient(conn net.Conn, bidChan chan<- Bid) {
    defer conn.Close()
    
    for {
        frame, err := ReadFrame(conn)  // Blocks here
        if err != nil {
            return
        }
        
        bid := parseBid(frame.Payload)  // Pure CPU work
        bidChan <- bid                  // Send to manager
    }
}

func main() {
    listener, _ := net.Listen("tcp", ":8080")
    bidChan := make(chan Bid, 5000)
    
    go manager(bidChan)  // Single manager goroutine
    
    for {
        conn, _ := listener.Accept()
        go handleClient(conn, bidChan)  // Spawn per connection
    }
}
```

**Why This Works:**

**1. M:N Scheduler**
- Go multiplexes M goroutines onto N OS threads (typically N = # CPU cores)
- When a goroutine blocks on I/O, the scheduler moves it off-CPU
- Other goroutines execute on that CPU core

**2. Netpoller Integration**
```
Goroutine calls conn.Read()
         ↓
Go runtime: "Is data available?"
         ↓ (no)
Park goroutine, add fd to epoll/kqueue
         ↓
Kernel: "fd 42 has data!"
         ↓
Netpoller wakes goroutine, schedules it
         ↓
Goroutine resumes with data
```

**3. CPU-Bound Work Parallelism**
Unlike Python's GIL, Go allows `parseBid()` to run on multiple cores simultaneously:
```
18 cores × 100% utilization = 18x CPU capacity vs. Python
```

**Performance:**
- **Goroutine overhead**: ~2KB stack vs. Python thread's ~8MB
- **Context switch**: ~200ns vs. OS thread's ~1-2μs
- **Max connections**: Limited by file descriptors, not memory

**Result:** **650k RPM** with 100% success rate.

---

### Decoupling with Buffered Channels

**Problem: Head-of-Line Blocking**

If the manager processes bids slowly, `bidChan <- bid` blocks the network goroutine:
```
Client sends bid → handleClient() tries to send on channel
                                  ↓ (channel full)
                          Goroutine blocks
                                  ↓
                    No more conn.Read() calls
                                  ↓
                      TCP buffer fills → backpressure
```

**Solution: Buffered Channel as Shock Absorber**
```go
bidChan := make(chan Bid, 5000)  // 5,000 slot buffer
```

**How it works:**
1. During burst traffic (1000 bids arrive in 100ms):
   - Network goroutines write to buffer instantly (no blocking)
   - Buffer fills to ~1200/5000 slots
2. Manager processes buffer at steady rate:
   - Drains ~10k bids/sec from channel
   - Buffer empties within 120ms

**Trade-off:**
- ✅ Decouples network layer from processing layer
- ✅ Tolerates 500ms spikes before dropping messages
- ❌ Uses ~80KB memory (5000 × 16 bytes per Bid struct)
- ❌ Not a replacement for backpressure (if sustained load > capacity, still fails)

---

## 4. State Management & Atomicity

### Problem: Race Conditions in Distributed Systems

**Naive approach (WRONG):**
```go
func processBid(auctionID int, amount float64) bool {
    current := redis.Get(fmt.Sprintf("auction:%d", auctionID))
    
    if amount > current {  // ⚠️ RACE WINDOW
        redis.Set(fmt.Sprintf("auction:%d", auctionID), amount)
        return true
    }
    return false
}
```

**The race:**
```
Time   Client A             Client B             Redis
───────────────────────────────────────────────────────
t0     GET auction:1                            →100
t1                          GET auction:1       →100
t2     (105 > 100)
t3                          (103 > 100)
t4     SET auction:1 105                        =105
t5                          SET auction:1 103   =103  ❌
```

Client A's winning bid (105) gets overwritten by Client B's lower bid (103).

**Why `sync.Mutex` doesn't help:**
```go
var mu sync.Mutex

func processBid(...) {
    mu.Lock()         // Only protects THIS process
    defer mu.Unlock()
    // ... same race condition across multiple servers
}
```

A mutex only prevents races within a single process. In a multi-node deployment:
- Server A's mutex doesn't know about Server B's mutex
- Both can read-then-write simultaneously

---

### Solution: Redis Lua Scripts for Atomic Execution

**Lua script (executed atomically inside Redis):**
```lua
-- compare_and_set.lua
local key = KEYS[1]
local new_bid = tonumber(ARGV[1])
local bidder = ARGV[2]

local current = redis.call('GET', key)

if not current or new_bid > tonumber(current) then
    redis.call('SET', key, new_bid)
    redis.call('SET', key .. ':bidder', bidder)
    redis.call('PUBLISH', 'bid_updates', key .. ':' .. new_bid)
    return 1  -- Success
end

return 0  -- Rejected (current bid higher)
```

**Go implementation:**
```go
script := redis.NewScript(`
    local key = KEYS[1]
    local new_bid = tonumber(ARGV[1])
    local current = redis.call('GET', key)
    
    if not current or new_bid > tonumber(current) then
        redis.call('SET', key, new_bid)
        return 1
    end
    return 0
`)

func processBid(auctionID int, amount float64) bool {
    result, err := script.Run(
        ctx,
        redis,
        []string{fmt.Sprintf("auction:%d", auctionID)},
        amount,
    ).Int()
    
    return result == 1
}
```

**Why this is atomic:**

Redis is **single-threaded** for command execution:
- Lua scripts execute without interruption
- No other commands can interleave during script execution
- The check-then-set happens in a single "transaction"

**Performance:**
- **1 network round-trip** (GET + conditional SET) vs. 2 separate calls
- **No distributed locking overhead** (no coordination between nodes)
- **Pub/Sub integration**: Script can publish bid updates in same atomic block

**Trade-offs:**
- ✅ Guarantees correctness even at 650k RPM
- ✅ Horizontally scalable (Redis Cluster can shard auctions by ID)
- ❌ Redis becomes single point of failure (mitigate with Redis Sentinel/Cluster)
- ❌ Lua is not type-safe (runtime errors possible)

---

## 5. Performance Bottlenecks & Solutions

### Bottleneck #1: TCP Listen Backlog Overflow

**Symptom:**
```
1000 concurrent users → 21% success rate
netstat: 11,053 failed connection attempts
```

**Root Cause:**

When `listener.Accept()` is called, the kernel maintains a **listen backlog queue**:
```
SYN packet arrives → Kernel adds to backlog → Accept() drains queue
```

Default backlog size (Windows): ~200 connections

**What happened:**
```
t=0ms:   Spawn 1000 goroutines
t=1ms:   All send SYN packets simultaneously
         Kernel queue: [200 connections]
         Kernel drops: 800 SYN packets
         
Clients retry SYN → Congestion → More drops → TCP collapse
```

**Solution: Connection Pacing**
```go
for i := 0; i < 1000; i++ {
    go connectAndBid()
    time.Sleep(3 * time.Millisecond)  // Stagger connection attempts
}
```

**Result:**
- 1ms pacing: 82% success rate
- 3ms pacing: **100% success rate**

**Why 3ms?**
```
Kernel processes 1 connection in ~3ms (handshake + accept)
200-slot queue / 3ms = ~66 connections/ms sustainable
1000 connections × 3ms = 3 seconds to connect all (well below timeout)
```

**Tuning options considered:**
1. Increase `listen()` backlog: `net.Listen("tcp", ":8080")` uses system default
2. TCP tuning: `tcp_max_syn_backlog` (requires root/admin)
3. Application-level: Rate limiting at client (✅ chosen for portability)

---

### Bottleneck #2: Idle Connection Timeout

**Symptom:**
```
Increased bid delay (10ms → 20ms) → Success rate dropped to 88%
```

**Root Cause:**

Holding 1,000 sockets open with infrequent traffic:
```
Connection established → Send 1 bid → Idle for 20ms → Send next bid
                                        ↓
                            TCP keepalive timeout (~15s on Windows)
                            OS reclaims resources prematurely
```

**Windows TCP behavior:**
- Idle socket = no data sent/received for N seconds
- OS marks socket for closure to free file descriptors
- Next `conn.Write()` → "connection reset by peer"

**Solution: Optimal Bid Cadence**
```go
const BidInterval = 10 * time.Millisecond  // Sweet spot

for i := 0; i < 50; i++ {
    sendBid(conn, auction, amount)
    time.Sleep(BidInterval)
}
```

**Result:**
- 10ms interval: 100% success (keeps connection "warm")
- 20ms interval: 88% success (too close to OS timeout heuristics)

**Alternative solutions:**
- TCP keepalive tuning: `conn.SetKeepAlive(true)` (not portable)
- Application-level heartbeat: Adds protocol complexity
- Shorter test duration: Doesn't reflect real-world usage

---

## 6. Trade-offs & Future Work

### Current Limitations

**1. Single Node Architecture**
- Redis is single point of failure
- Cannot scale beyond 1 machine's network bandwidth (~10 Gbps)

**2. No Authentication**
- Binary protocol has no auth layer
- Assumes trusted network (localhost testing)

**3. Fixed Buffer Sizes**
- 5,000-slot channel buffer tuned for this workload
- May overflow under different traffic patterns

**4. Lack of Observability**
- No Prometheus metrics
- No distributed tracing (OpenTelemetry)
- Debugging production issues would be difficult

---

### Production Readiness Roadmap

**Phase 1: Reliability**
- [ ] Redis Cluster for horizontal scaling
- [ ] Circuit breaker for Redis failures
- [ ] Graceful shutdown (drain in-flight requests)
- [ ] Connection pooling for Redis client

**Phase 2: Observability**
- [ ] Prometheus metrics (RPS, latency percentiles, error rate)
- [ ] Structured logging (Zerolog)
- [ ] Distributed tracing (spans for bid processing)
- [ ] Grafana dashboard

**Phase 3: Scale**
- [ ] Multi-node deployment (load balancer + multiple servers)
- [ ] Redis Pub/Sub for cross-node bid broadcasts
- [ ] Rate limiting per user (token bucket)
- [ ] Auto-scaling based on CPU/memory metrics

**Phase 4: Security**
- [ ] TLS for TCP connections
- [ ] JWT authentication
- [ ] Rate limiting by IP
- [ ] DDoS protection (SYN cookies, connection limits)

---

### Lessons Learned

**1. Language choice is a strategic decision**
- Python's GIL was the limiting factor, not the algorithm
- Go's concurrency primitives (goroutines, channels) are production-grade

**2. Measure, don't guess**
- Without the benchmark suite, "self-DDoS" would've looked like a bug
- `netstat` revealed the real bottleneck (OS, not application)

**3. Systems engineering is iterative**
- 21% → 82% → 100% success rate required multiple tuning passes
- Each bottleneck revealed the next layer to optimize

**4. Trade-offs are inevitable**
- Binary protocol = performance, but loses debuggability
- Buffered channels = throughput, but adds latency
- Redis Lua = correctness, but single point of failure

---

## References

- [Go Scheduler Design](https://github.com/golang/go/blob/master/src/runtime/proc.go)
- [Redis Lua Scripting](https://redis.io/docs/manual/programmability/eval-intro/)
- [TCP Listen Backlog](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html#tcp-variables)
- [Benchmarking Methodology](https://github.com/PrachiJha-404/High-Throughput-Auction-Server/tree/main/benchmarks)