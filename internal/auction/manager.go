package auction

import (
	"context"
	"fmt"
	"log"

	redis "github.com/go-redis/redis/v8"
)

// var ctx = context.Background()

// bidScript should be imported or defined from redis.go
var bidScript = redis.NewScript(`
    local current_bid = tonumber(redis.call('get', KEYS[1]) or 0)
    local new_bid = tonumber(ARGV[1])
    
    if new_bid > current_bid then
        redis.call('set', KEYS[1], new_bid)
        -- Publish the update: "amount:user"
        redis.call('publish', 'auction_updates', ARGV[1] .. ":" .. ARGV[2])
        return 1
    else
        return 0
    end
`)

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

func NewManager(rdb *redis.Client) *Manager {
	return &Manager{
		Bids:        make(chan BidEvent, 100),
		redisClient: rdb, // Use the one passed in!
	}
}

//Lua script in redis.go

func (m *Manager) Run() {
	ctx := context.Background()
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
