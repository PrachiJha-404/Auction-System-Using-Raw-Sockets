# Architectural Decision Records (ADR)

This document details the engineering choices that enable Jackfruit to handle high-frequency bidding at scale.

## 1. Raw TCP Sockets vs. WebSockets
For this engine, raw TCP was chosen over WebSockets to minimize overhead:
* **Payload Efficiency:** WebSockets include a framing header (2-14 bytes) and masking for client-to-server data. Raw TCP allows for a strict 6-byte header.
* **Handshake Overhead:** WebSockets require an HTTP-based "Upgrade" handshake, adding latency.
* **Protocol Control:** Raw sockets allowed the implementation of a custom **Type-Length-Value (TLV)** protocol for faster binary parsing.

## 2. Go (Goroutines) vs. Python (Asyncio)
The project was migrated from Python to Go to utilize hardware more effectively:
* **Parallelism:** Python's Global Interpreter Lock (GIL) restricts execution to a single core for CPU-bound tasks. Go's scheduler utilizes all **18 logical CPUs**.
* **Lightweight Concurrency:** Go routines start with only ~2KB of stack, enabling 100,000+ concurrent connections.
* **Non-blocking I/O:** Go’s netpoller uses efficient system calls (epoll/kqueue) to handle thousands of connections without blocking OS threads.



## 3. Event-Driven vs. Per-Thread Architecture
Traditional per-thread models fail under load due to context-switching costs.
* **Resource Optimization:** Thousands of logical goroutines are multiplexed onto a small pool of OS threads.
* **Scalability:** By avoiding "one-thread-per-client," the system maintains high throughput even as connection counts increase.

## 4. Redis (Lua) vs. Global Mutex Lock
A local `sync.Mutex` is insufficient for a distributed system:
* **Distributed Locking:** A mutex only protects state within a single process. In a multi-node cluster, Redis provides a centralized source of truth.
* **Atomic Transactions:** Using **Redis Lua scripts** ensures that "check-then-set" operations (verifying if a new bid is higher) happen atomically in a single round-trip.
* **Pub/Sub Backplane:** Redis Pub/Sub acts as the system's "backplane," allowing a bid accepted on Server A to be broadcast to clients on Server B instantly.