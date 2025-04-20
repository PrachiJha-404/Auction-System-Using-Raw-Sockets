import socket
# import sys
import selectors #need it for multiple sockets
import time

#for now a list of hardcoded items and prices to bid, later we can let clients put up the bids

items_to_bid = [
    {"id": 1, "name": "Vintage Watch", "description": "A rare vintage watch", "starting_bid": 100, "highest_bid": 0, "highest_bidder": None},
    {"id": 2, "name": "Antique Vase", "description": "A beautiful antique vase", "starting_bid": 50, "highest_bid": 0, "highest_bidder": None},
    {"id": 3, "name": "Classic Car", "description": "A 1965 Mustang", "starting_bid": 5000, "highest_bid": 0, "highest_bidder": None},
    {"id": 4, "name": "Gaming Laptop", "description": "A high-end gaming laptop", "starting_bid": 1500, "highest_bid": 0, "highest_bidder": None},
    {"id": 5, "name": "Smartphone", "description": "Latest model smartphone", "starting_bid": 700, "highest_bid": 0, "highest_bidder": None}
]

clients = []
current_item_index = 0



selector = selectors.DefaultSelector()

#TODO: Make a list of clients to iterate through for broadcast

def broadcast_to_all(clients, message):
    for client in clients:
        client.send(message.encode())

def start_countdown_and_announce(clients, item):
    broadcast_to_all(clients, f"The current highest bid is {item['highest_bid']} for {item['name']} by {item['highest_bidder']}")

    #Start countdown
    countdown = 3
    while countdown>0:
        time.sleep(2)
        broadcast_to_all(clients, f"Countdown started: {countdown}")
        countdown -= 1

    broadcast_to_all(clients, "SOLD!")


def accept_connection(sock, current_item):
    conn, addr = sock.accept()
    print(f"Got a connection from {addr}")
    conn.setblocking(False)
    clients.append(conn)
    selector.register(conn, selectors.EVENT_READ, read_request)
    send_auction_details(conn, current_item)


def read_request(conn, current_item):
    data = conn.recv(1024)
    if data:
        handle_bid(conn, data, current_item)
    else:
        selector.unregister(conn)
        conn.close()

def handle_bid(conn, bid_data, current_item):
    try:
        bid_amount = int(bid_data.decode())
    except ValueError:
        conn.send("Enter valid bid amount!".encode())
        return

    
    if bid_amount> current_item['highest_bid']:
        current_item["highest_bid"] = bid_amount
        current_item["highest_bidder"] = conn.getpeername()
        conn.send(f"Your bid of {bid_amount} is now the highest bid for {current_item['name']}!".encode())
        start_countdown_and_announce(current_item, clients) #, conn.getpeername(), bid_amount)
        return True
    else:
        conn.send(f"Your bid of {bid_amount} is too low! Current highest bid is {current_item['highest_bid']}".encode())

def send_auction_details(conn, current_item):
    
    item_details = f"Item ID: {current_item['id']}, Name: {current_item['name']}, Description: {current_item['description']}, Starting Bid: {current_item['starting_bid']}"
    conn.send(item_details.encode())
    conn.send("Place your bids:".encode())

def auction_not_over(current_item_index):
    if (current_item_index >= len(items_to_bid)):
        return False
    return True

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

    while current_item_index < len(items_to_bid):
        current_item = items_to_bid[current_item_index]
        broadcast_to_all(clients, f"Next item: {current_item['name']}")

        while auction_not_over(current_item_index):
            events = selector.select()

            for key, _ in events:
                callback = key.data
                callback(key.fileobj, current_item)

            broadcast_to_all(clients, f"{current_item['name']} SOLD to {current_item['highest_bidder']} for {current_item['higehst_bid']}")
            current_item_index += 1

if __name__ == '__main__':
        start_server()
