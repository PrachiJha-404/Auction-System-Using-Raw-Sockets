import socket
# import sys
import selectors #need it for multiple sockets

#for now a list of hardcoded items and prices to bid, later we can let clients put up the bids

items_to_bid = [
    {"id": 1, "name": "Vintage Watch", "description": "A rare vintage watch", "starting_bid": 100, "highest_bid": 0, "highest_bidder": None},
    {"id": 2, "name": "Antique Vase", "description": "A beautiful antique vase", "starting_bid": 50, "highest_bid": 0, "highest_bidder": None},
    {"id": 3, "name": "Classic Car", "description": "A 1965 Mustang", "starting_bid": 5000, "highest_bid": 0, "highest_bidder": None},
    {"id": 4, "name": "Gaming Laptop", "description": "A high-end gaming laptop", "starting_bid": 1500, "highest_bid": 0, "highest_bidder": None},
    {"id": 5, "name": "Smartphone", "description": "Latest model smartphone", "starting_bid": 700, "highest_bid": 0, "highest_bidder": None}
]



selector = selectors.DefaultSelector()

def accept_connection(sock):
    conn, addr = sock.accept()
    print(f"Got a connection from {addr}")
    conn.setblocking(False)
    selector.register(conn, selectors.EVENT_READ, read_request)

def read_request(conn):
    data = conn.recv(1024)
    if data:
        handle_bid(conn, data)
    else:
        selector.unregister(conn)
        conn.close()

def handle_bid(conn, bid_data):
    try:
        bid_amount = int(bid_data.decode())
    except ValueError:
        conn.send("Enter valid bid amount!".encode())
        return

    for item in items_to_bid:
        if bid_amount> item['highest_bid']:
            item["highest_bid"] = bid_amount
            item["highest_bidder"] = conn.getpeername()
            conn.send(f"Your bid of {bid_amount} is now the highest bid for {item['name']}!".encode())

        else:
            conn.send(f"Your bid of {bid_amount} is too low! Current highest bid is {item['highest_bid']}".encode())

def send_auction_details(conn):
    for item in items_to_bid:
        item_details = f"Item ID: {item['id']}, Name: {item['name']}, Description: {item['description']}, Starting Bid: {item['starting_bid']}"
        conn.send(item_details.encode())
        conn.send("Place your bids:".encode())

def start_server():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #we are using IPv4 and TCP
        print("socket successfully created!!!")
    except socket.error as err:
        print(f"socket creation failed with {err}")
    #HOST = "127.0.0.1"
    PORT = 65432 #non-privileged ports are greater than 1023
    #port was a string before hence the error

    s.bind(('', PORT)) 
    #bind expects a single argument which is a tuple of the host and port!!!
    print(f"socket binded to {PORT}")

    s.listen(5) #we'll keep maximum 5 people waiting if server is at its max capacity and can't connect
    print("socket is listening")

    s.setblocking(False)

    selector.register(s, selectors.EVENT_READ, accept_connection)

    while True:
        events = selector.select()

        for key, _ in events:
            callback = key.data
            callback(key.fileobj)

if __name__ == '__main__':
        start_server()
