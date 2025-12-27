import socket
import threading
import time
import sys

# Configuration - Match your Go bench settings
CONCURRENCY = 1000
BIDS_PER_USER = 50
SERVER_ADDR = ("127.0.0.1", 65432)

stats = {
    "success": 0,
    "errors": 0,
    "latencies": []
}
stats_lock = threading.Lock()

def simulate_user(user_id):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(SERVER_ADDR)
        
        # The Python server sends a welcome message immediately
        sock.recv(1024) 

        for i in range(BIDS_PER_USER):
            bid_amount = 1000 + (user_id * 10) + i
            message = f"{bid_amount}\n" # Python server uses .strip()
            
            start_time = time.perf_counter()
            try:
                sock.sendall(message.encode())
                # We don't necessarily wait for a response to maximize throughput
                # but we track the send success
                duration = time.perf_counter() - start_time
                
                with stats_lock:
                    stats["success"] += 1
                    stats["latencies"].append(duration)
            except:
                with stats_lock:
                    stats["errors"] += 1
            
            # Match the 10ms sleep from your Go bench
            time.sleep(0.01)
            
        sock.close()
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1

def run_test():
    threads = []
    print(f" Starting Python Stress Test: {CONCURRENCY} users...")
    start_total = time.perf_counter()

    for i in range(CONCURRENCY):
        t = threading.Thread(target=simulate_user, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.perf_counter() - start_total
    total_reqs = stats["success"] + stats["errors"]
    rps = stats["success"] / total_time

    print("\n---  Python Performance Report ---")
    print(f"Total Bids Attempted: {total_reqs}")
    print(f"Success Rate:        {(stats['success']/total_reqs)*100:.2f}%")
    print(f"Total Time:          {total_time:.4f}s")
    print(f"Throughput:          {rps:.2f} Requests/Sec")
    print(f"Throughput (RPM):    {rps*60:.2f} Requests/Min")

if __name__ == "__main__":
    run_test()