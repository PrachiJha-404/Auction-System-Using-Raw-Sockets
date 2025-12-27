package manager

import (
	"fmt"
)

type BidEvent struct {
	Amount int
	User   string
}

type Manager struct {
	Bids        chan BidEvent //channel, our conveyor belt
	HighestBid  int
	WinningUser string
}

func NewManager() *Manager {
	return &Manager{
		Bids: make(chan BidEvent, 100), //Buffered channel
	}
}

func (m *Manager) Run() {
	fmt.Println("Aunction Manager started...")
	for bid := range m.Bids {
		if bid.Amount > m.HighestBid {
			m.HighestBid = bid.Amount
			m.WinningUser = bid.User
			fmt.Printf("New Leader: %s with %d\n", m.WinningUser, m.HighestBid)
		}
	}
}
