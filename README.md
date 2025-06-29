# Real-Time Auction System

A simple real-time auction system built with Python using sockets and threading. This project allows multiple clients to connect to a server and participate in timed auctions for various items. It simulates a real-time bidding environment with countdowns, live updates, and competitive bidding.


---

## Features

- **Client-Server Architecture**: Built using `socket` and `selectors` libraries for real-time bid communication.
- **Auction Countdown**: Each item is auctioned with a countdown timer that resets on each valid bid.
- **Broadcast Messages**: Server broadcasts bid updates to all connected clients.
- **Thread-Safe Bid Handling**: Threading locks are used to prevent race conditions in concurrent bidding scenarios.
- **Smart Disconnection Handling**: Graceful removal of disconnected clients from the server.
- **Preloaded Items**: A list of 5 sample items is included to auction automatically.

---

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/real-time-auction-system.git
cd real-time-auction-system
```

### 2. Start the server

```bash
python server.py
```

The server will:

- Start listening on localhost:65432
- Begin auctioning items automatically
- Accept connections from multiple clients

### 3. Start one or more clients

``` bash
python client.py
```

Optionally, you can specify a custom server IP and port

``` bash
python client.py <server_ip> <port>
```

---

## Usage Instructions

- After connecting, the client will receive updates about the item currently being auctioned.
- Enter your bid amount when prompted.
- To exit the bidding process, type quit.
- Only bids higher than the current bid are accepted. Once a bid is placed, a 10-second countdown begins. If no other bid is received during this time, the item is sold.

--- 

## Dependencies

No external dependencies required. 
This project uses in-built Python modules. 

- `socket`
- `selectors`
- `threading`
- `sys`
- `time`

---

## Future Improvements

- GUI using tkinter or PyQt

- Authentication and user registration

- Bid history and analytics

- WebSocket-based implementation for web clients




