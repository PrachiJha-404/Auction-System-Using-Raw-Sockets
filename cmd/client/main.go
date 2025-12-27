package main

import (
	"auction/internal/protocol"
	"bufio"
	"fmt"
	"log"
	"net"
	"os"
)

func main() {
	// 1. Connect to the server
	conn, err := net.Dial("tcp", "localhost:65432")
	if err != nil {
		log.Fatal("Could not connect to server:", err)
	}
	defer conn.Close()

	fmt.Println("Connected to Auction Server!")
	fmt.Println("---------------------------")

	// 2. The Listener: Runs in the background to catch broadcasts
	go func() {
		for {
			// protocol.ReadFrame handles our 6-byte header + payload logic
			frame, err := protocol.ReadFrame(conn)
			if err != nil {
				fmt.Println("\n[System] Connection lost.")
				os.Exit(0)
			}

			// If the server sends an Update type, print it
			if frame.Type == protocol.TypeUpdate {
				fmt.Printf("\n[BROADCAST]: %s\n> ", string(frame.Payload))
			}
		}
	}()

	// 3. The Sender: Main thread stays here to read your keyboard
	scanner := bufio.NewScanner(os.Stdin)
	fmt.Print("> Enter your bid: ")

	for scanner.Scan() {
		bidText := scanner.Text()
		if bidText == "" {
			continue
		}

		// Wrap the bid in our custom Frame and send it
		// TypeBid (0x01) tells the server this is a new bid
		err := protocol.WriteFrame(conn, protocol.TypeBid, []byte(bidText))
		if err != nil {
			log.Println("Failed to send bid:", err)
			break
		}
		fmt.Print("> ")
	}
}
