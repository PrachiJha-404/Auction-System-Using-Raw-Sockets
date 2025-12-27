package auction

import (
	"context"

	redis "github.com/go-redis/redis/v8"
)

var ctx = context.Background()

func NewRedisClient() *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})
}

var bidScrip = redis.NewScript(`
	local current_bid = tonumber(redis.call('get', KEYS[1]) or 0)
	local new_bid = tonumber(ARGV[1])
	if new_bid>current_bid then
		redis.call('set', KEYS[1], new_bid)
		--Notify all other server instances via Pub Sub channel
		redis.call('publish', 'auction_updates', ARGV[1] .. ":" .. ARGV[2])
		return 1 --Success
	else
		return 0 --Rejected
	end
`)
