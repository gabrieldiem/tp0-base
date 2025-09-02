package common

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

var NETWORK_ENDIANNESS = binary.BigEndian

const (
	// MESSAGE_DELIMITER defines the character used to delimit messages.
	MESSAGE_DELIMITER = '\n'
)

type Socket struct {
	serverAddress string
	conn          net.Conn
}

func NewSocket(serverAddress string) Socket {
	return Socket{
		serverAddress: serverAddress,
		conn:          nil,
	}
}

// createClientSocket establishes a TCP connection to the configured
// server address. If the connection fails, the error is logged and
// returned. On success, the connection is stored in the client.
func (s *Socket) Init() error {
	conn, err := net.Dial("tcp", s.serverAddress)
	if err != nil {
		return err
	}

	s.conn = conn
	return nil
}

func (s *Socket) Cleanup() error {
	return s.conn.Close()
}

func (s *Socket) SendMessage(msg Message) error {
	raw_msg := msg.ToBytes(NETWORK_ENDIANNESS)
	err := s.sendAll(raw_msg)
	if err != nil {
		return err
	}

	return nil
}

const (
	SIZEOF_UINT16 = 2
	SIZEOF_UINT32 = 4
)

func (s *Socket) ReceiveMessage() (Message, error) {
	// Read msgType
	header := make([]byte, SIZEOF_UINT16)
	if _, err := io.ReadFull(s.conn, header); err != nil {
		return nil, fmt.Errorf("failed to read msgType: %w", err)
	}
	msgType := NETWORK_ENDIANNESS.Uint16(header)

	// Read length
	lenBuf := make([]byte, SIZEOF_UINT32)
	if _, err := io.ReadFull(s.conn, lenBuf); err != nil {
		return nil, fmt.Errorf("failed to read length: %w", err)
	}
	length := NETWORK_ENDIANNESS.Uint32(lenBuf)

	// Read value
	payload := make([]byte, length)
	if _, err := io.ReadFull(s.conn, payload); err != nil {
		return nil, fmt.Errorf("failed to read payload: %w", err)
	}

	// Decode based on msgType
	switch msgType {
	case MSG_TYPE_REGISTER_BET:
		return DecodeMsgRegisterBet(payload, NETWORK_ENDIANNESS)
	case MSG_TYPE_REGISTER_BET_OK:
		return DecodeMsgRegisterBetOk(payload, NETWORK_ENDIANNESS)
	case MSG_TYPE_REGISTER_BET_FAILED:
		return DecodeMsgRegisterBetFailed(payload, NETWORK_ENDIANNESS)
	default:
		return nil, fmt.Errorf("unknown message type: %d", msgType)
	}
}

// sendAll writes the entire message to the TCP connection, retrying
// until all bytes are sent or an error occurs.
func (s *Socket) sendAll(data []byte) error {
	total := 0

	for total < len(data) {
		n, err := s.conn.Write(data[total:])
		if err != nil {
			return fmt.Errorf("failed to write to connection: %w", err)
		}
		total += n
	}
	return nil
}
