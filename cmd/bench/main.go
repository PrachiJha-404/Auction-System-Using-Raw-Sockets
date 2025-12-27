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
		concurrency = 1000 // Number of concurrent "users"
		bidsPerUser = 50   // Bids sent by each user
		serverAddr  = "localhost:65432"
	)

	var wg sync.WaitGroup
	start := time.Now()

	var (
		successCount int
		errorCount   int
		mu           sync.Mutex
	)

	fmt.Printf("Starting High-Performance Stress Test\n")
	fmt.Printf("Config: %d users | %d bids each | Total: %d requests\n",
		concurrency, bidsPerUser, concurrency*bidsPerUser)
	fmt.Println("--------------------------------------------------")

	for i := 0; i < concurrency; i++ {
		wg.Add(1)

		go func(id int) {
			defer wg.Done()

			// 1. Establish connection
			conn, err := net.Dial("tcp", serverAddr)
			if err != nil {
				mu.Lock()
				errorCount += bidsPerUser // If connection fails, all bids for this user fail
				mu.Unlock()
				return
			}
			defer conn.Close()

			// 2. Burst bidding loop
			for j := 0; j < bidsPerUser; j++ {
				bidAmount := 1000 + (id * 10) + j
				payload := []byte(fmt.Sprintf("%d", bidAmount))

				// Send the binary frame
				err := protocol.WriteFrame(conn, protocol.TypeBid, payload)

				mu.Lock()
				if err == nil {
					successCount++
				} else {
					errorCount++
				}
				mu.Unlock()

				// Simulate slight delay between bids from the same user
				time.Sleep(10 * time.Millisecond)
			}
		}(i)

		// --- THE FIX: PACING ---
		// We wait 1ms before spawning the next user.
		// This spreads 1,000 connections over 1 second,
		// preventing a Windows TCP Backlog overflow.
		time.Sleep(3 * time.Millisecond)
	}

	wg.Wait()
	duration := time.Since(start)
	totalRequests := concurrency * bidsPerUser
	rps := float64(successCount) / duration.Seconds()

	fmt.Println("Final Performance Report\n")
	fmt.Printf("Total Bids Attempted: %d\n", totalRequests)
	fmt.Printf("Successful Bids:      %d\n", successCount)
	fmt.Printf("Failed/Dropped:       %d\n", errorCount)
	fmt.Printf("Success Rate:         %.2f%%\n", (float64(successCount)/float64(totalRequests))*100)
	fmt.Printf("Total Test Time:      %v\n", duration)
	fmt.Printf("Actual Throughput:    %.2f Requests/Sec\n", rps)
	fmt.Printf("Actual RPM:           %.2f Requests/Min\n", rps*60)
	fmt.Println("--------------------------------------------------")
	fmt.Printf("System Stats: %d Logical CPUs | %d Goroutines active\n",
		runtime.NumCPU(), runtime.NumGoroutine())
}
