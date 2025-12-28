# High-Throughput Auction Server

A real-time auction engine built in **Go** and **Redis**. It is designed to handle high-concurrency bidding environments with sub-millisecond latency, achieving a peak throughput of **650k+ RPM** with **100%** success rate on a single node.

## Performance Metrics
* **Peak Throughput:** 650209 Requests/Minute (10,836 Requests/Second).
* **Concurrency:** 100+ concurrent TCP streams across 18 logical cores.
* **Success Rate:** 100.00% under burst load testing.
* **Optimization:** 4.6x throughput improvement** (150k → 650k RPM)

## Tech Stack
* **Language:** Go (Golang)
* **Database:** Redis (Lua Scripting for atomicity)
* **Protocol:** TCP with custom binary framing (Type-Length-Value)
* **Messaging:** Redis Pub/Sub for event-driven broadcasts

## Quick Start

### Prerequisites
- Go 1.21+
- Docker (for Redis)
- Windows/Linux/macOS

### Run the Server
```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Clone and run
git clone https://github.com/PrachiJha-404/High-Throughput-Auction-Server
cd High-Throughput-Auction-Server
go run cmd/server/main.go
```

### Run Benchmarks
```bash
go run cmd/bench/main.go
```

Expected output: ~650k RPM with 100% success rate (1k users, 3ms pacing)

For a deep dive into the design, see [ARCHITECTURE.md](./ARCHITECTURE.md).

**Read the full story:** [How this server got so fast it overwhelmed the Windows TCP stack](https://dev.to/prachi_awesome_jha/my-go-server-was-so-fast-it-self-ddosd-my-laptop-48i2)