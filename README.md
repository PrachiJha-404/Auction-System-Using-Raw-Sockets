# High-Performance Distributed Auction Engine

This is a distributed, real-time auction engine built in **Go** and **Redis**. It is designed to handle high-concurrency bidding environments with sub-millisecond latency, achieving a peak throughput of **442k+ RPM** on a single node.

## 📊 Performance Metrics
* **Peak Throughput:** 442,622 Requests/Minute (7,377 Requests/Second).
* **Concurrency:** 100+ concurrent TCP streams across 18 logical cores.
* **Success Rate:** 100.00% under burst load testing.
* **Optimization:** 70x increase in throughput compared to legacy Python implementation.

## 🛠️ Tech Stack
* **Language:** Go (Golang)
* **Database:** Redis (Lua Scripting for atomicity)
* **Protocol:** Raw TCP with custom Binary TLV Framing
* **Messaging:** Redis Pub/Sub for event-driven broadcasts

## 🚀 Getting Started
1. **Start Redis:** `docker run -d -p 6379:6379 redis`
2. **Run Server:** `go run cmd/server/main.go`
3. **Run Benchmark:** `go run cmd/bench/main.go`

For a deep dive into the design, see [ARCHITECTURE.md](./ARCHITECTURE.md).