package common

import (
	"bytes"
	"encoding/binary"
)

const (
	// Message type identifiers used in the protocol
	MSG_TYPE_REGISTER_BETS       = 1
	MSG_TYPE_REGISTER_BET_OK     = 2
	MSG_TYPE_REGISTER_BET_FAILED = 3
	MSG_TYPE_ACK                 = 4
)

// Message is the interface implemented by all protocol messages.
// Each message must be able to serialize itself into bytes.
type Message interface {
	ToBytes(endianness binary.ByteOrder) []byte
}

// MsgRegisterBetOk represents a message confirming that a bet (or batch of bets)
// was successfully registered by the server.
type MsgRegisterBetOk struct {
	msgType uint16
}

// MsgRegisterBetFailed represents a message indicating that a bet registration
// failed. It includes an error code describing the failure.
type MsgRegisterBetFailed struct {
	msgType    uint16
	error_code uint16
}

// MsgRegisterBets represents a message sent by the client to register
// one or more bets with the server.
type MsgRegisterBets struct {
	msgType        uint16
	numberOfBets   uint32
	betsToRegister []Bet
}

// Confirmation of reception message
type MsgAck struct {
	msgType uint16
}

// NewMsgRegisterBetOk creates a new MsgRegisterBetOk message
func NewMsgRegisterBetOk(dni, number uint32) MsgRegisterBetOk {
	return MsgRegisterBetOk{
		msgType: MSG_TYPE_REGISTER_BET_OK,
	}
}

// NewMsgRegisterBetFailed creates a new MsgRegisterBetFailed message
// with the given error code.
func NewMsgRegisterBetFailed(dni, number uint32, error_code uint16) MsgRegisterBetFailed {
	return MsgRegisterBetFailed{
		msgType:    MSG_TYPE_REGISTER_BET_FAILED,
		error_code: error_code,
	}
}

// NewMsgRegisterBets creates a new MsgRegisterBets message containing
// the given slice of bets.
func NewMsgRegisterBets(bets []Bet) MsgRegisterBets {
	return MsgRegisterBets{
		msgType:        MSG_TYPE_REGISTER_BETS,
		numberOfBets:   uint32(len(bets)),
		betsToRegister: bets,
	}
}

// NewMsgAck creates a new MsgAck message
func NewMsgAck() MsgAck {
	return MsgAck{
		msgType: MSG_TYPE_ACK,
	}
}

// ToBytes serializes MsgRegisterBetOk into binary format:
//
// | msg_type (2 bytes) |
func (msg MsgRegisterBetOk) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	return buf.Bytes()
}

// ToBytes serializes MsgRegisterBetFailed into binary format:
//
// | msg_type (2 bytes) | error_code (2 bytes) |
func (msg MsgRegisterBetFailed) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	// Write error code
	binary.Write(buf, endianness, msg.error_code)

	return buf.Bytes()
}

// ToBytes serializes MsgRegisterBets into binary format:
//
// | msg_type (2 bytes) |
// | number_of_bets (4 bytes) |
// For each bet:
//
//	| bet_len (8 bytes) | bet (bet_len bytes) |
func (msg MsgRegisterBets) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write MSG_TYPE
	binary.Write(buf, endianness, msg.msgType)

	// Write NUMBER_OF_BETS
	binary.Write(buf, endianness, msg.numberOfBets)

	// Write each bet with its length prefix
	for _, bet := range msg.betsToRegister {
		rawBet := bet.ToBytes(endianness)
		rawBetLen := int64(len(rawBet))

		// Write bet length
		binary.Write(buf, endianness, rawBetLen)

		// Write serialized bet
		buf.Write(rawBet)
	}

	return buf.Bytes()
}

// ToBytes serializes MsgAck into binary format:
//
// | msg_type (2 bytes) |
func (msg MsgAck) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	return buf.Bytes()
}

// GetOverheadInBytes calculates the protocol overhead in bytes for a batch
// of bets. The overhead includes:
//
//   - msg_type (2 bytes)
//   - number_of_bets (4 bytes)
//   - bet_len (8 bytes) for each bet
//
// This does not include the actual serialized bet data.
func GetOverheadInBytes(numberOfBets int) int {
	overhead := 0

	// Overhead of MSG_TYPE
	overhead += SIZEOF_UINT16

	// Overhead of NUMBER_OF_BETS
	overhead += SIZEOF_UINT32

	// Overhead of all bets, each one has the overhead of its length
	overhead += SIZEOF_INT64 * numberOfBets

	return overhead
}
