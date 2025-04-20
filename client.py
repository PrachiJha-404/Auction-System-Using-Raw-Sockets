import socket
import threading
import sys
import time

def receive_messages(sock):
    """Continuously receive and display messages from the server"""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("Disconnected from server")
                break
            print(f"Received: {data.decode()}")
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def main():
    # Create a socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Server connection details (default to localhost)
    HOST = "127.0.0.1"
    PORT = 65432
    
    # Allow custom server and port from command line
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    
    try:
        # Connect to the server
        print(f"Connecting to auction server at {HOST}:{PORT}...")
        client_socket.connect((HOST, PORT))
        print("Connected to the auction server!")
        
        # Start a thread to receive messages from the server
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.daemon = True
        receive_thread.start()
        
        # Main loop for placing bids
        print("Enter your bid amount when you want to place a bid (or 'quit' to exit):")
        while True:
            try:
                bid_input = input()
                if bid_input.lower() == 'quit':
                    break
                
                # Try to convert the input to an integer
                try:
                    bid_amount = int(bid_input)
                    # Send the bid to the server
                    client_socket.send(str(bid_amount).encode())
                except ValueError:
                    print("Please enter a valid number for your bid")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Closing connection")
        client_socket.close()

if __name__ == "__main__":
    main()