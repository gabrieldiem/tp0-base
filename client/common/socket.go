package common

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

var NETWORK_ENDIANNESS = binary.BigEndian

const (
	// MESSAGE_DELIMITER defines the character used to delimit messages.
	MESSAGE_DELIMITER      = '\n'
	SINGLE_ITEM_BUFFER_LEN = 1
)

type Socket struct {
	serverAddress string
	conn          net.Conn
	closed        bool
}

func NewSocket(serverAddress string) Socket {
	return Socket{
		serverAddress: serverAddress,
		conn:          nil,
		closed:        false,
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
	if s.conn != nil && !s.closed {
		s.closed = true
		return s.conn.Close()
	}
	return nil
}

func (s *Socket) SendMessage(msg Message, ctx context.Context) error {
	rawMsg := msg.ToBytes(NETWORK_ENDIANNESS)

	done := make(chan error, SINGLE_ITEM_BUFFER_LEN)
	go func() {
		done <- s.sendAll(rawMsg)
	}()

	select {
	case <-ctx.Done():
		s.Cleanup()
		return ctx.Err()
	case err := <-done:
		return err
	}
}

const (
	SIZEOF_UINT16 = 2
	SIZEOF_UINT32 = 4
)

type DecodeResult struct {
	msg Message
	err error
}

func NewDecodeResult(msg Message, err error) DecodeResult {
	return DecodeResult{
		msg: msg,
		err: err,
	}
}

func (s *Socket) decodeMessage(msgType uint16, payload []byte, done chan DecodeResult) {
	switch msgType {
	case MSG_TYPE_REGISTER_BET:
		m, err := DecodeMsgRegisterBet(payload, NETWORK_ENDIANNESS)
		done <- NewDecodeResult(m, err)
	case MSG_TYPE_REGISTER_BET_OK:
		m, err := DecodeMsgRegisterBetOk(payload, NETWORK_ENDIANNESS)
		done <- NewDecodeResult(m, err)
	case MSG_TYPE_REGISTER_BET_FAILED:
		m, err := DecodeMsgRegisterBetFailed(payload, NETWORK_ENDIANNESS)
		done <- NewDecodeResult(m, err)
	default:
		done <- NewDecodeResult(nil, fmt.Errorf("unknown message type: %d", msgType))
	}
}

func (s *Socket) decodeHeader(done chan DecodeResult) (uint16, []byte) {
	header := make([]byte, SIZEOF_UINT16)
	lenBuf := make([]byte, SIZEOF_UINT32)

	// Read msgType
	if _, err := io.ReadFull(s.conn, header); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read msgType: %w", err))
		return 0, nil
	}
	msgType := NETWORK_ENDIANNESS.Uint16(header)

	// Read length
	if _, err := io.ReadFull(s.conn, lenBuf); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read length: %w", err))
		return 0, nil
	}
	length := NETWORK_ENDIANNESS.Uint32(lenBuf)

	// Read payload
	payload := make([]byte, length)
	if _, err := io.ReadFull(s.conn, payload); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read payload: %w", err))
		return 0, nil
	}

	return msgType, payload
}

func (s *Socket) ReceiveMessage(ctx context.Context) (Message, error) {
	done := make(chan DecodeResult, SINGLE_ITEM_BUFFER_LEN)

	go func() {
		msgType, payload := s.decodeHeader(done)
		if payload != nil {
			s.decodeMessage(msgType, payload, done)
		}
	}()

	select {
	case <-ctx.Done():
		s.Cleanup()
		return nil, ctx.Err()
	case result := <-done:
		return result.msg, result.err
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
