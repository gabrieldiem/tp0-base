package common

import (
	"bytes"
	"encoding/binary"
)

const (
	MSG_TYPE_REGISTER_BETS       = 1
	MSG_TYPE_REGISTER_BET_OK     = 2
	MSG_TYPE_REGISTER_BET_FAILED = 3
)

// Message is the interface implemented by all protocol messages.
// Each message must be able to serialize itself into bytes.
type Message interface {
	ToBytes(endianness binary.ByteOrder) []byte
}

// MsgRegisterBetOk represents a message confirming a bet was registered.
type MsgRegisterBetOk struct {
	msgType uint16
}

// MsgRegisterBetFailed represents a message indicating a bet registration failed.
type MsgRegisterBetFailed struct {
	msgType    uint16
	error_code uint16
}

// MsgRegisterBet represents a message to register a bet.
type MsgRegisterBets struct {
	msgType        uint16
	numberOfBets   uint32
	betsToRegister []Bet
}

// NewMsgRegisterBetOk creates a new MsgRegisterBetOk with the given dni and number.
func NewMsgRegisterBetOk(dni, number uint32) MsgRegisterBetOk {
	return MsgRegisterBetOk{
		msgType: MSG_TYPE_REGISTER_BET_OK,
	}
}

// NewMsgRegisterBetFailed creates a new MsgRegisterBetFailed with the given values.
func NewMsgRegisterBetFailed(dni, number uint32, error_code uint16) MsgRegisterBetFailed {
	return MsgRegisterBetFailed{
		msgType:    MSG_TYPE_REGISTER_BET_FAILED,
		error_code: error_code,
	}
}

// NewMsgRegisterBet creates a new MsgRegisterBet with the given bet.
func NewMsgRegisterBets(bets []Bet) MsgRegisterBets {
	return MsgRegisterBets{
		msgType:        MSG_TYPE_REGISTER_BETS,
		numberOfBets:   uint32(len(bets)),
		betsToRegister: bets,
	}
}

// ToBytes serializes MsgRegisterBetOk into binary format:
// | msg_type (2 bytes) | dni (4 bytes) | number (4 bytes) |
func (msg MsgRegisterBetOk) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	binary.Write(buf, endianness, msg.msgType)

	return buf.Bytes()
}

// ToBytes serializes MsgRegisterBetFailed into binary format:
// | msg_type (2 bytes) | dni (4 bytes) | number (4 bytes) | error_code (2 bytes) |
func (msg MsgRegisterBetFailed) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	binary.Write(buf, endianness, msg.msgType)
	binary.Write(buf, endianness, msg.error_code)

	return buf.Bytes()
}

// ToBytes serializes MsgRegisterBets into binary format:
// | msg_type (2 bytes) | number_of_bets (4 bytes) | bet_len (8 bytes) | bet (bet_len bytes) |
func (msg MsgRegisterBets) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write MSG_TYPE
	binary.Write(buf, endianness, msg.msgType)

	// Write NUMBER_OF_BETS
	binary.Write(buf, endianness, msg.numberOfBets)

	for _, bet := range msg.betsToRegister {
		raw_bet := bet.ToBytes(endianness)
		raw_bet_len := int64(len(raw_bet))

		// Write bet length
		binary.Write(buf, endianness, raw_bet_len)

		// Write raw bet
		buf.Write(raw_bet)
	}

	return buf.Bytes()
}

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
