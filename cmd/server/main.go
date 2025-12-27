package main

import (
	frame "auction/internal/protocol"
	"log"
	"net"
)

func main() {
	//Connecting to server
	conn, err := net.Dial("tcp", "localhost:65432")
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	//Prepare a bid
	bidAmount := []byte("500")

	//sending using our frame
	err = frame.WriteFrame(conn, frame.TypeBid, bidAmount)
	if err != nil {
		log.Printf("Failed to send bid: %v", err)
	}
	log.Println("Bid sent succesfully.")
}
