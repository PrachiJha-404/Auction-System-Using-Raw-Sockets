package main

import (
	"auction/internal/protocol"
	"fmt"
	"net"
	"runtime"
	"sync"
	"time"
)

func main() {
	const (
		concurrency = 100 // Number of concurrent "users"
		bidsPerUser = 50  // Bids sent by each user
		serverAddr  = "localhost:65432"
	)

	var wg sync.WaitGroup
	start := time.Now()

	successCount := 0
	var mu sync.Mutex

	fmt.Printf("Starting stress test: %d users, %d bids each...\n", concurrency, bidsPerUser)

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			conn, err := net.Dial("tcp", serverAddr)
			if err != nil {
				return
			}
			defer conn.Close()

			for j := 0; j < bidsPerUser; j++ {
				bidAmount := 1000 + (id * 10) + j
				payload := []byte(fmt.Sprintf("%d", bidAmount))

				err := protocol.WriteFrame(conn, protocol.TypeBid, payload)
				if err == nil {
					mu.Lock()
					successCount++
					mu.Unlock()
				}
				// Small sleep to simulate realistic human speed
				time.Sleep(10 * time.Millisecond)
			}
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)
	totalRequests := concurrency * bidsPerUser
	rps := float64(totalRequests) / duration.Seconds()

	fmt.Println("\n--- Performance Report ---")
	fmt.Printf("Total Bids Sent:  %d\n", totalRequests)
	fmt.Printf("Success Rate:     %.2f%%\n", (float64(successCount)/float64(totalRequests))*100)
	fmt.Printf("Total Time:       %v\n", duration)
	fmt.Printf("Throughput:       %.2f Requests/Sec\n", rps)
	fmt.Printf("Throughput (RPM): %.2f Requests/Min\n", rps*60)
	fmt.Printf("Logical CPUs: %d\n", runtime.NumCPU())
	fmt.Printf("Active Goroutines: %d\n", runtime.NumGoroutine())
}
