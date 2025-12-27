package auction

import (
	"fmt"
	"log"

	redis "github.com/go-redis/redis/v8"
)

// bidScript should be imported or defined from redis.go
var bidScript *redis.Script

type BidEvent struct {
	Amount int
	User   string
}

type Manager struct {
	Bids chan BidEvent //channel, our conveyor belt
	// HighestBid  int
	// WinningUser string
	redisClient *redis.Client
}

func NewManager() *Manager {
	redisClient := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})
	return &Manager{
		Bids:        make(chan BidEvent, 100), //Buffered channel
		redisClient: redisClient,
	}
}

//Lua script in redis.go

func (m *Manager) Run() {
	fmt.Println("Aunction Manager started...")
	for bid := range m.Bids {
		// 1. Attempt to update state in Redis atomically
		// KEYS[1] is "auction:price"
		// ARGV[1] is amount, ARGV[2] is username
		result, err := bidScript.Run(ctx, m.redisClient, []string{"auction:price"}, bid.Amount, bid.User).Result()
		if err != nil {
			log.Printf("Redis Error: %v", err)
			continue
		}
		if result.(int64) == 1 {
			fmt.Printf("Bid accepted: %d by %s\n", bid.Amount, bid.User)
		} else {
			fmt.Printf("Bid rejected: %d by %s (Too low)\n", bid.Amount, bid.User)
		}
	}

}

// func (m *Manager) ProcessBid(user string, amount int) bool {
// 	//KEYS[1]: "current_bid"
// 	//ARGV[1]: amount, ARGV[2]: user_id
// 	result, err := auction.bidScript.Run(ctx, m.redisClient, []string{auction:price}, bid.Amount, bid.User).Result()
// 	if err != nil {
// 		return false
// 	}
// 	return result.(int64) == 1
// }
