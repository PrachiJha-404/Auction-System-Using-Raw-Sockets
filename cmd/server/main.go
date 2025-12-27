package main

import (
	"auction/internal/auction"
	"auction/internal/network"
	"auction/internal/protocol"
	"context"
	"log"

	"github.com/go-redis/redis/v8"
)

var ctx = context.Background()

func main() {
	//1. Setting up redis
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6739",
	})
	//2. Setup the Auction Manager (Logic)
	mgr := auction.NewManager(rdb)
	go mgr.Run()
	//3. Setup network server
	srv := network.NewServer(":65432", mgr)
	//4. Listen and broadcast updates
	go func() {
		pubsub := rdb.Subscribe(ctx, "auction_updates")
		defer pubsub.Close()

		log.Println("Redis Subscriber: Waiting for auction updates...")
		for msg := range pubsub.Channel() {
			broadcastMsg := "NEW LEADER: " + msg.Payload
			srv.Broadcast(protocol.TypeUpdate, []byte(broadcastMsg))
		}
	}()
	// 5. Start the TCP Listener (Blocking call)
	log.Println("Auction Server starting on :65432...")
	if err := srv.Start(); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}

}
