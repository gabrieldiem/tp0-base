package common

import (
	"bufio"
	"fmt"
	"net"
)

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
	raw_msg := msg.ToBytes()
	err := s.sendAll(raw_msg)
	if err != nil {
		return err
	}

	return nil
}

func (s *Socket) ReceiveMessage() (Message, error) {
	a := bufio.NewReader(s.conn).ReadString(MESSAGE_DELIMITER)

	return NewMsgRegisterBetOk(0, 0), nil
}

// receiveMessage reads a single message from the server until the
// MESSAGE_DELIMITER is encountered. Logs the received message or
// an error if reading fails.
func (s *Socket) receiveMessage() error {
	msg, err := c.readAll()

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
		c.config.ID,
		msg,
	)
	return nil
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
