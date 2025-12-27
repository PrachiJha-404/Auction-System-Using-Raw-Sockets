//Network server handles the connection management

package network

import (
	"auction/internal/auction"
	"auction/internal/protocol"
	"log"
	"net"
	"strconv"
	"sync"
)

type Server struct {
	Addr    string
	Clients map[net.Conn]bool
	Mu      sync.Mutex //Protects the clients map
	Manager *auction.Manager
}

func (s *Server) handleConnection(conn net.Conn) {
	defer func() { //Resource Leak Prevention
		s.Mu.Lock()
		delete(s.Clients, conn)
		s.Mu.Unlock()
		conn.Close()
	}()

	for {
		frame, err := protocol.ReadFrame(conn)
		if err != nil {
			return //End goroutine
			//Because no frame?
		}
		if frame.Type == protocol.TypeBid {
			payload, err := strconv.Atoi(string(frame.Payload))
			if err != nil {
				continue
			}
			amount := payload
			user := conn.RemoteAddr().String()
			s.Manager.Bids <- auction.BidEvent{
				Amount: amount,
				User:   user,
			}
		}
	}
}

func (s *Server) Start() error {
	ln, err := net.Listen("tcp", s.Addr)
	if err != nil {
		log.Fatal(err)
		return err
	}
	for {
		conn, err := ln.Accept()
		if err != nil {
			continue //If one connection fails, we can't stop the whole server
		}
		//Add user to clients map using mutex
		s.Mu.Lock()
		s.Clients[conn] = true
		s.Mu.Unlock()
		log.Printf("New connection from %s", conn.RemoteAddr())
		go s.handleConnection(conn) //Listener for this specific connection
	}
	return nil
}

func (s *Server) Broadcast(msgType byte, payload []byte) {
	s.Mu.Lock()
	defer s.Mu.Unlock()
	// payload := []byte(msg)
	for conn := range s.Clients {

		err := protocol.WriteFrame(conn, msgType, payload)
		if err != nil {
			log.Printf("Failed to broadcast to %s: %v", conn.RemoteAddr(), err)
		}
	}
}

func NewServer(addr string, mgr *auction.Manager) *Server {
	return &Server{
		Addr:    addr,
		Clients: make(map[net.Conn]bool),
		Manager: mgr,
	}
}
