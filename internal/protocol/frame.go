package protocol

import (
	"encoding/binary"
	"fmt"
	"io"
)

//Defining message types

const (
	TypeBid       byte = 0x01
	TypeUpdate    byte = 0x02
	TypeInventory byte = 0x03
	TypeErr       byte = 0x04
)

const HeaderSize = 6 //1b vers + 1b Type + 4b length

type Frame struct {
	Version byte
	Type    byte
	Payload []byte
}

func WriteFrame(w io.Writer, msgType byte, payload []byte) error {
	header := make([]byte, HeaderSize)
	header[0] = 1
	header[1] = msgType
	binary.BigEndian.PutUint32(header[2:], uint32(len(payload)))
	_, err := w.Write(append(header, payload...))
	return err
}

func ReadFrame(r io.Reader) (*Frame, error) {
	header := make([]byte, HeaderSize)
	_, err := io.ReadFull(r, header) //Waits until all 6 bytes arrive
	if err != nil {
		return nil, err
	}
	version := header[0]
	msgType := header[1]
	length := binary.BigEndian.Uint32(header[2:])

	if length > 1024*1024 {
		//We set a 1MB limit for the payload
		return nil, fmt.Errorf("payload too large: %d", length)
	}

	payload := make([]byte, length)
	_, err = io.ReadFull(r, payload)
	if err != nil {
		return nil, err
	}
	return &Frame{
		Version: version,
		Type:    msgType,
		Payload: payload,
	}, nil
}
