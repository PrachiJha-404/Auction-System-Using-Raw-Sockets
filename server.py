import socket
import selectors
import time
import threading

# List of items to auction
items_to_bid = [
    {"id": 1, "name": "Vintage Watch", "description": "A rare vintage watch", "starting_bid": 100, "highest_bid": 100, "highest_bidder": None},
    {"id": 2, "name": "Antique Vase", "description": "A beautiful antique vase", "starting_bid": 50, "highest_bid": 50, "highest_bidder": None},
    {"id": 3, "name": "Classic Car", "description": "A 1965 Mustang", "starting_bid": 5000, "highest_bid": 5000, "highest_bidder": None},
    {"id": 4, "name": "Gaming Laptop", "description": "A high-end gaming laptop", "starting_bid": 1500, "highest_bid": 1500, "highest_bidder": None},
    {"id": 5, "name": "Smartphone", "description": "Latest model smartphone", "starting_bid": 700, "highest_bid": 700, "highest_bidder": None}
]

# Initialize variables
clients = []  # List to store client connections
current_item_index = 0  # Index of the current item being auctioned
selector = selectors.DefaultSelector()
auction_in_progress = False
auction_lock = threading.Lock()  # Lock for thread safety
active_timers = []  # List to track all active timers

def cancel_all_timers():
    """Cancel all active timers"""
    global active_timers
    for timer in active_timers:
        timer.cancel()
    active_timers = []

def broadcast_to_all(message):
    """Send a message to all connected clients"""
    print(f"Broadcasting: {message}")
    # Make a copy of the clients list to avoid issues if it changes during iteration
    current_clients = clients.copy()
    for client in current_clients:
        try:
            client.send(f"{message}\n".encode())
        except:
            # If sending fails, close and remove the client
            try:
                selector.unregister(client)
                client.close()
                clients.remove(client)
            except:
                pass

def run_countdown(item):
    """Run a countdown and then declare the item sold"""
    global auction_in_progress
    
    # Use lock to ensure thread safety
    with auction_lock:
        current_name = item['name']  # Remember which item we're counting down for
        
        # Verify we're still auctioning this item (could have changed due to race condition)
        if not auction_in_progress or current_item_index > 0 and items_to_bid[current_item_index-1]['name'] != current_name:
            print(f"Countdown for {current_name} cancelled - no longer the current item")
            return
    
    # Start countdown
    for i in range(10, 0, -1):
        # Check if this countdown should still run
        with auction_lock:
            if not auction_in_progress or current_item_index > 0 and items_to_bid[current_item_index-1]['name'] != current_name:
                print(f"Countdown for {current_name} cancelled during countdown")
                return
        
        broadcast_to_all(f"Bidding for {current_name} ends in {i} seconds...")
        time.sleep(1)
    
    # Item sold
    with auction_lock:
        # Check one more time this is still the current item
        if not auction_in_progress or current_item_index > 0 and items_to_bid[current_item_index-1]['name'] != current_name:
            print(f"Sale for {current_name} cancelled - no longer the current item")
            return
            
        if item['highest_bidder']:
            bidder_addr = item['highest_bidder']
            broadcast_to_all(f"SOLD! {current_name} goes to bidder at {bidder_addr[0]}:{bidder_addr[1]} for ${item['highest_bid']}")
        else:
            broadcast_to_all(f"No bids received for {current_name}. Item not sold.")
        
        # Start the next auction
        next_auction_timer = threading.Timer(2.0, start_next_auction)
        active_timers.append(next_auction_timer)
        next_auction_timer.start()

def start_next_auction():
    """Start the auction for the next item"""
    global current_item_index, auction_in_progress
    
    # Use lock to ensure thread safety
    with auction_lock:
        # Cancel any existing timers
        cancel_all_timers()
        
        # Check if we've auctioned all items
        if current_item_index >= len(items_to_bid):
            broadcast_to_all("All items have been auctioned. Thank you for participating!")
            auction_in_progress = False
            return
        
        # Get the current item and increment the index for next time
        item = items_to_bid[current_item_index]
        current_item_index += 1
        
        # Reset the highest bid to the starting bid
        item['highest_bid'] = item['starting_bid']
        item['highest_bidder'] = None
        
        # Announce the new item
        broadcast_to_all(f"=== NEW AUCTION ITEM ===")
        broadcast_to_all(f"Item #{item['id']}: {item['name']}")
        broadcast_to_all(f"Description: {item['description']}")
        broadcast_to_all(f"Starting bid: ${item['starting_bid']}")
        broadcast_to_all(f"Please place your bids now!")
        
        # Start the auction countdown in a separate thread
        auction_in_progress = True
        countdown_timer = threading.Timer(30.0, run_countdown, [item])
        active_timers.append(countdown_timer)
        countdown_timer.start()

def accept_connection(sock):
    """Accept a new client connection"""
    conn, addr = sock.accept()
    print(f"New connection from {addr}")
    conn.setblocking(False)
    clients.append(conn)
    selector.register(conn, selectors.EVENT_READ, read_request)
    
    # Send welcome message
    conn.send("Welcome to the Real-Time Auction System!\n".encode())
    
    # If an auction is in progress, send the current item details
    with auction_lock:
        if auction_in_progress and current_item_index > 0 and current_item_index <= len(items_to_bid):
            item = items_to_bid[current_item_index - 1]
            conn.send(f"Currently auctioning: {item['name']} (current bid: ${item['highest_bid']})\n".encode())

def read_request(conn):
    """Read and process data from a client"""
    try:
        data = conn.recv(1024)
        if data:
            handle_bid(conn, data)
        else:
            # Client disconnected
            print(f"Client {conn.getpeername()} disconnected")
            selector.unregister(conn)
            clients.remove(conn)
            conn.close()
    except Exception as e:
        print(f"Error reading from client: {e}")
        try:
            selector.unregister(conn)
            clients.remove(conn)
            conn.close()
        except:
            pass

def handle_bid(conn, bid_data):
    """Process a bid from a client"""
    with auction_lock:
        if not auction_in_progress:
            conn.send("No auction currently in progress.\n".encode())
            return
        
        # Get the current item
        if current_item_index > 0 and current_item_index <= len(items_to_bid):
            current_item = items_to_bid[current_item_index - 1]
        else:
            conn.send("No item currently being auctioned.\n".encode())
            return
        
        # Parse the bid
        try:
            bid_amount = int(bid_data.decode().strip())
        except ValueError:
            conn.send("Please enter a valid number for your bid.\n".encode())
            return
        
        # Check if the bid is valid
        if bid_amount <= current_item['highest_bid']:
            conn.send(f"Your bid must be higher than the current bid of ${current_item['highest_bid']}.\n".encode())
            return
        
        # Cancel existing timers for the current auction
        cancel_all_timers()
        
        # Update the highest bid
        current_item['highest_bid'] = bid_amount
        current_item['highest_bidder'] = conn.getpeername()
        
        # Notify everyone about the new bid
        broadcast_to_all(f"New bid! ${bid_amount} for {current_item['name']} from bidder at {conn.getpeername()[0]}:{conn.getpeername()[1]}")
        conn.send(f"Your bid of ${bid_amount} is now the highest! Awaiting more bids...\n".encode())
        
        # Start a new countdown for this bid
        countdown_timer = threading.Timer(10.0, run_countdown, [current_item])
        active_timers.append(countdown_timer)
        countdown_timer.start()

def start_server():
    """Start the auction server"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Socket successfully created!")
    except socket.error as err:
        print(f"Socket creation failed with error: {err}")
        return
    
    PORT = 65432
    
    try:
        server_socket.bind(('', PORT))
        print(f"Socket bound to port {PORT}")
    except socket.error as err:
        print(f"Socket binding failed with error: {err}")
        return
    
    server_socket.listen(5)
    print("Server is listening for connections...")
    
    server_socket.setblocking(False)
    selector.register(server_socket, selectors.EVENT_READ, accept_connection)
    
    print("Starting the auction...")
    initial_timer = threading.Timer(2.0, start_next_auction)
    active_timers.append(initial_timer)
    initial_timer.start()
    
    try:
        while True:
            events = selector.select(timeout=1)  # Add timeout for more responsive shutdown
            for key, _ in events:
                callback = key.data
                if callback == accept_connection:
                    callback(key.fileobj)
                else:
                    callback(key.fileobj)
    except KeyboardInterrupt:
        print("Server shutting down...")
        cancel_all_timers()
    finally:
        cancel_all_timers()
        selector.close()
        server_socket.close()

if __name__ == '__main__':
    start_server()