package common

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

// NETWORK_ENDIANNESS defines the byte order used for encoding/decoding
// all protocol messages. The protocol uses Big Endian.
var NETWORK_ENDIANNESS = binary.BigEndian

const (
	// SINGLE_ITEM_BUFFER_LEN is the buffer size for internal channels
	// used in goroutines for send/receive operations.
	SINGLE_ITEM_BUFFER_LEN = 1

	// Sizes of primitive types in bytes
	SIZEOF_UINT16 = 2
	SIZEOF_UINT32 = 4
	SIZEOF_UINT64 = 8
	SIZEOF_INT64  = 8
)

// Socket wraps a TCP connection and provides methods for
// initialization, cleanup, sending, and receiving protocol messages.
type Socket struct {
	serverAddress string // server address in "host:port" format
	conn          net.Conn
	closed        bool
}

// NewSocket creates a new Socket with the given server address.
// The connection is not established until Init() is called.
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
// It marks the socket as closed to prevent double-closing.
func (s *Socket) Cleanup() error {
	if s.conn != nil && !s.closed {
		s.closed = true
		return s.conn.Close()
	}
	return nil
}

// SendMessage serializes a Message and writes it to the connection.
// The send operation is performed in a goroutine, and cancellation
// is supported via the provided context.
func (s *Socket) SendMessage(msg Message, ctx context.Context) error {
	rawMsg := msg.ToBytes(NETWORK_ENDIANNESS)

	done := make(chan error, SINGLE_ITEM_BUFFER_LEN)
	go func() {
		// Attempt to send all bytes
		done <- s.sendAll(rawMsg)
	}()

	select {
	case <-ctx.Done():
		// Context cancelled → cleanup connection
		s.Cleanup()
		return ctx.Err()
	case err := <-done:
		return err
	}
}

// DecodeResult holds the result of decoding a message.
// It is used to communicate between goroutines and the main loop.
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

// decodeMessage decodes a message payload into a specific Message type
// based on the given msgType. It returns a DecodeResult containing
// either the decoded message or an error.
func (s *Socket) decodeMessage(msgType uint16, done chan DecodeResult) DecodeResult {
	switch msgType {
	case MSG_TYPE_REGISTER_BET_OK:
		m, err := s.decodeMsgRegisterBetOk()
		return NewDecodeResult(m, err)
	case MSG_TYPE_REGISTER_BET_FAILED:
		m, err := s.decodeMsgRegisterBetFailed(done)
		return NewDecodeResult(m, err)
	case MSG_TYPE_INFORM_WINNERS:
		m, err := s.decodeMsgInformWinners(done)
		return NewDecodeResult(m, err)
	default:
		return NewDecodeResult(nil, fmt.Errorf("unknown message type: %d", msgType))
	}
}

// decodeHeader reads the message header (msgType) from the connection.
// It returns the message type or writes an error to the channel if reading fails.
func (s *Socket) decodeHeader(done chan DecodeResult) (uint16, error) {
	header := make([]byte, SIZEOF_UINT16)

	// Read msgType
	if _, err := io.ReadFull(s.conn, header); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read msgType: %w", err))
		return 0, err
	}
	msgType := NETWORK_ENDIANNESS.Uint16(header)
	return msgType, nil
}

// ReceiveMessage reads a message from the connection.
// It spawns a goroutine to decode the header and payload,
// then decodes the message type. It supports cancellation
// via the provided context.
func (s *Socket) ReceiveMessage(ctx context.Context) (Message, error) {
	done := make(chan DecodeResult, SINGLE_ITEM_BUFFER_LEN)

	go func() {
		defer close(done)

		// First, decode the header (msgType)
		msgType, err := s.decodeHeader(done)

		if err == nil {
			// Decode the message body based on msgType
			result := s.decodeMessage(msgType, done)
			done <- result
			return
		}

		// If header decoding failed, propagate error
		done <- NewDecodeResult(nil, fmt.Errorf("failed to decode header"))
	}()

	select {
	case <-ctx.Done():
		// Context cancelled → cleanup connection
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

// decodeMsgRegisterBetOk deserializes a MsgRegisterBetOk from the connection.
// Since MsgRegisterBetOk only contains a msgType, no additional bytes are read.
func (s *Socket) decodeMsgRegisterBetOk() (Message, error) {
	return MsgRegisterBetOk{
		msgType: MSG_TYPE_REGISTER_BET_OK,
	}, nil
}

// decodeMsgRegisterBetFailed deserializes a MsgRegisterBetFailed from the connection.
// It reads the errorCode (2 bytes) following the msgType.
func (s *Socket) decodeMsgRegisterBetFailed(done chan DecodeResult) (Message, error) {
	errorCodeBuffer := make([]byte, SIZEOF_UINT16)

	// Read errorCode
	if _, err := io.ReadFull(s.conn, errorCodeBuffer); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read errorCode: %w", err))
		return nil, nil
	}
	errorCode := NETWORK_ENDIANNESS.Uint16(errorCodeBuffer)

	return MsgRegisterBetFailed{
		msgType:    MSG_TYPE_REGISTER_BET_FAILED,
		error_code: errorCode,
	}, nil
}

// decodeMsgInformWinners deserializes a MsgInformWinners from the connection.
func (s *Socket) decodeMsgInformWinners(done chan DecodeResult) (Message, error) {
	// Read number_of_dni_winners (8 bytes)
	numWinnersBuf := make([]byte, SIZEOF_UINT64)

	if _, err := io.ReadFull(s.conn, numWinnersBuf); err != nil {
		done <- NewDecodeResult(nil, fmt.Errorf("failed to read number_of_dni_winners: %w", err))
		return nil, err
	}
	numWinners := NETWORK_ENDIANNESS.Uint64(numWinnersBuf)

	// Read each winner (4 bytes each)
	dniWinners := make([]uint32, numWinners)

	for i := uint64(0); i < numWinners; i++ {
		dniBuf := make([]byte, SIZEOF_UINT32)

		if _, err := io.ReadFull(s.conn, dniBuf); err != nil {
			done <- NewDecodeResult(nil, fmt.Errorf("failed to read dni_winner[%d]: %w", i, err))
			return nil, err
		}
		dniWinners[i] = NETWORK_ENDIANNESS.Uint32(dniBuf)
	}

	// Construct the message
	return MsgInformWinners{
		msgType:    MSG_TYPE_INFORM_WINNERS,
		DniWinners: dniWinners,
	}, nil
}
