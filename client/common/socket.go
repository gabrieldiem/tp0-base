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
	// SINGLE_ITEM_BUFFER_LEN is the buffer size for internal channels.
	SINGLE_ITEM_BUFFER_LEN = 1

	SIZEOF_UINT16 = 2
	SIZEOF_UINT32 = 4
	SIZEOF_INT64  = 8
)

// Socket wraps a TCP connection and provides methods for
// initialization, cleanup, sending, and receiving messages.
type Socket struct {
	serverAddress string
	conn          net.Conn
	closed        bool
}

// NewSocket creates a new Socket with the given server address.
func NewSocket(serverAddress string) Socket {
	return Socket{
		serverAddress: serverAddress,
		conn:          nil,
		closed:        false,
	}
}

// Init establishes a TCP connection to the configured server address.
// On success, the connection is stored in the Socket.
func (s *Socket) Init() error {
	conn, err := net.Dial("tcp", s.serverAddress)
	if err != nil {
		return err
	}

	s.conn = conn
	return nil
}

// Cleanup closes the connection if it is open and not already closed.
func (s *Socket) Cleanup() error {
	if s.conn != nil && !s.closed {
		s.closed = true
		return s.conn.Close()
	}
	return nil
}

// SendMessage serializes a Message and writes it to the connection.
// It runs the send operation in a goroutine and supports cancellation
// via the provided context.
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

// DecodeResult holds the result of decoding a message.
type DecodeResult struct {
	msg Message
	err error
}

// NewDecodeResult creates a new DecodeResult with the given values.
func NewDecodeResult(msg Message, err error) DecodeResult {
	return DecodeResult{
		msg: msg,
		err: err,
	}
}

// decodeMessage decodes a payload into a specific Message type
// based on the given msgType and sends the result to the channel.
func (s *Socket) decodeMessage(msgType uint16, payload []byte) DecodeResult {
	switch msgType {
	case MSG_TYPE_REGISTER_BET_OK:
		m, err := DecodeMsgRegisterBetOk(NETWORK_ENDIANNESS)
		return NewDecodeResult(m, err)
	case MSG_TYPE_REGISTER_BET_FAILED:
		m, err := DecodeMsgRegisterBetFailed(payload, NETWORK_ENDIANNESS)
		return NewDecodeResult(m, err)
	default:
		return NewDecodeResult(nil, fmt.Errorf("unknown message type: %d", msgType))
	}
}

// decodeHeader reads the message header and payload from the connection.
// It returns the message type and payload bytes, or writes an error
// to the channel if reading fails.
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

// ReceiveMessage reads a message from the connection.
// It spawns a goroutine to decode the header and payload,
// then decodes the message type. It supports cancellation
// via the provided context.
func (s *Socket) ReceiveMessage(ctx context.Context) (Message, error) {
	done := make(chan DecodeResult, SINGLE_ITEM_BUFFER_LEN)

	go func() {
		defer close(done)

		msgType, payload := s.decodeHeader(done)
		if payload != nil {
			result := s.decodeMessage(msgType, payload)
			done <- result
			return
		}

		done <- NewDecodeResult(nil, fmt.Errorf("failed to decode header"))
	}()

	select {
	case <-ctx.Done():
		s.Cleanup()
		return nil, ctx.Err()
	case result := <-done:
		return result.msg, result.err
	}
}

// sendAll writes the entire data slice to the connection,
// retrying until all bytes are sent or an error occurs.
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
