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
	MSG_TYPE_ALL_BETS_SENT       = 5
	MSG_TYPE_REQUEST_WINNERS     = 6
	MSG_TYPE_INFORM_WINNERS      = 7
)

// Message is the interface implemented by all protocol messages.
// Each message must be able to serialize itself into bytes.
type Message interface {
	ToBytes(endianness binary.ByteOrder) []byte
}

// MsgRegisterBetOk represents a server → client message confirming
// that a bet (or batch of bets) was successfully registered.
type MsgRegisterBetOk struct {
	msgType uint16
}

// MsgRegisterBetFailed represents a server → client message indicating
// that a bet registration failed. It includes an error code describing the failure.
type MsgRegisterBetFailed struct {
	msgType    uint16
	error_code uint16
}

// MsgRegisterBets represents a client → server message used to register
// one or more bets. Each bet is serialized with its length prefix.
type MsgRegisterBets struct {
	msgType        uint16
	numberOfBets   uint32
	betsToRegister []Bet
}

// MsgAck represents a client → server message acknowledging
// that the previous message was received.
type MsgAck struct {
	msgType uint16
}

// MsgAllBetsSent represents a client → server message notifying
// that the client has finished sending all bets.
type MsgAllBetsSent struct {
	msgType uint16
}

// MsgRequestWinners represents a client → server message requesting
// the list of winning bets.
type MsgRequestWinners struct {
	msgType uint16
}

// MsgInformWinners represents a server → client message containing
// the list of winning bettors’ DNIs.
type MsgInformWinners struct {
	msgType    uint16
	DniWinners []uint32
}

// NewMsgRegisterBetOk creates a new MsgRegisterBetOk message.
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

// NewMsgAck creates a new MsgAck message.
func NewMsgAck() MsgAck {
	return MsgAck{
		msgType: MSG_TYPE_ACK,
	}
}

// NewMsgAllBetsSent creates a new MsgAllBetsSent message.
func NewMsgAllBetsSent() MsgAllBetsSent {
	return MsgAllBetsSent{
		msgType: MSG_TYPE_ALL_BETS_SENT,
	}
}

// NewMsgRequestWinners creates a new MsgRequestWinners message.
func NewMsgRequestWinners() MsgRequestWinners {
	return MsgRequestWinners{
		msgType: MSG_TYPE_REQUEST_WINNERS,
	}
}

// NewMsgInformWinners creates a new MsgInformWinners message
// containing the given list of DNI winners.
func NewMsgInformWinners(dniWinners []uint32) MsgInformWinners {
	return MsgInformWinners{
		msgType:    MSG_TYPE_INFORM_WINNERS,
		DniWinners: dniWinners,
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

// ToBytes serializes MsgAllBetsSent into binary format:
//
// | msg_type (2 bytes) |
func (msg MsgAllBetsSent) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	return buf.Bytes()
}

// ToBytes serializes MsgRequestWinners into binary format:
//
// | msg_type (2 bytes) |
func (msg MsgRequestWinners) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	return buf.Bytes()
}

// ToBytes serializes MsgInformWinners into binary format:
//
// | msg_type (2 bytes) |
// | number_of_dni_winners (8 bytes) |
// | dni_winner_1 (4 bytes) | ... | dni_winner_n (4 bytes) |
func (msg MsgInformWinners) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	// Write message type
	binary.Write(buf, endianness, msg.msgType)

	// Only write winners if there are any
	if len(msg.DniWinners) > 0 {
		// Write number of winners (8 bytes)
		binary.Write(buf, endianness, uint64(len(msg.DniWinners)))

		// Write each winner DNI (4 bytes each)
		for _, dni := range msg.DniWinners {
			binary.Write(buf, endianness, dni)
		}
	}

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
