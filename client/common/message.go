package common

import (
	"bytes"
	"encoding/binary"
	"time"
)

const (
	MSG_TYPE_REGISTER_BET        = 1
	MSG_TYPE_REGISTER_BET_OK     = 2
	MSG_TYPE_REGISTER_BET_FAILED = 3
)

type Message interface {
	ToBytes(endianness binary.ByteOrder) []byte
}

type MsgRegisterBet struct {
	msgType       uint16
	betToRegister Bet
}

type MsgRegisterBetOk struct {
	msgType uint16
	dni     uint32
	number  uint32
}

type MsgRegisterBetFailed struct {
	msgType    uint16
	dni        uint32
	number     uint32
	error_code uint16
}

func NewMsgRegisterBet(bet Bet) MsgRegisterBet {
	return MsgRegisterBet{
		msgType:       MSG_TYPE_REGISTER_BET,
		betToRegister: bet,
	}
}

func NewMsgRegisterBetOk(dni, number uint32) MsgRegisterBetOk {
	return MsgRegisterBetOk{
		msgType: MSG_TYPE_REGISTER_BET_OK,
		dni:     dni,
		number:  number,
	}
}

func NewMsgRegisterBetFailed(dni, number uint32, error_code uint16) MsgRegisterBetFailed {
	return MsgRegisterBetFailed{
		msgType:    MSG_TYPE_REGISTER_BET_FAILED,
		dni:        dni,
		number:     number,
		error_code: error_code,
	}
}

/*
| msg_type (2 bytes) | bet_len (8 bytes) | bet (bet_len bytes)
*/
func (msg MsgRegisterBet) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)
	raw_bet := msg.betToRegister.ToBytes(endianness)
	raw_bet_len := int64(len(raw_bet))

	// Write MSG_TYPE
	binary.Write(buf, endianness, msg.msgType)

	// Write bet length
	binary.Write(buf, endianness, raw_bet_len)

	// Write raw bet
	buf.Write(raw_bet)

	return buf.Bytes()
}

func (msg MsgRegisterBetOk) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	binary.Write(buf, endianness, msg.msgType)
	binary.Write(buf, endianness, msg.dni)
	binary.Write(buf, endianness, msg.number)

	return buf.Bytes()
}

func (msg MsgRegisterBetFailed) ToBytes(endianness binary.ByteOrder) []byte {
	buf := new(bytes.Buffer)

	binary.Write(buf, endianness, msg.msgType)
	binary.Write(buf, endianness, msg.dni)
	binary.Write(buf, endianness, msg.number)
	binary.Write(buf, endianness, msg.error_code)

	return buf.Bytes()
}

func DecodeMsgRegisterBet(payload []byte, endianness binary.ByteOrder) (Message, error) {
	buf := bytes.NewReader(payload)

	// Name
	var nameLen uint32
	binary.Read(buf, endianness, &nameLen)
	nameBytes := make([]byte, nameLen)
	buf.Read(nameBytes)

	// Surname
	var surnameLen uint32
	binary.Read(buf, endianness, &surnameLen)
	surnameBytes := make([]byte, surnameLen)
	buf.Read(surnameBytes)

	// Dni
	var dni uint32
	binary.Read(buf, endianness, &dni)

	// Birthdate
	var birthUnix int64
	binary.Read(buf, endianness, &birthUnix)

	// Number
	var number uint32
	binary.Read(buf, endianness, &number)

	// Form Bet
	bet := Bet{
		Name:      string(nameBytes),
		Surname:   string(surnameBytes),
		Dni:       int(dni),
		Birthdate: time.Unix(birthUnix, 0),
		Number:    int(number),
	}

	return MsgRegisterBet{
		msgType:       MSG_TYPE_REGISTER_BET,
		betToRegister: bet,
	}, nil
}

func DecodeMsgRegisterBetOk(payload []byte, endianness binary.ByteOrder) (Message, error) {
	buf := bytes.NewReader(payload)

	var dni uint32
	binary.Read(buf, endianness, &dni)

	var number uint32
	binary.Read(buf, endianness, &number)

	return MsgRegisterBetOk{
		msgType: MSG_TYPE_REGISTER_BET_OK,
		dni:     dni,
		number:  number,
	}, nil
}

func DecodeMsgRegisterBetFailed(payload []byte, endianness binary.ByteOrder) (Message, error) {
	buf := bytes.NewReader(payload)

	var dni uint32
	binary.Read(buf, endianness, &dni)

	var number uint32
	binary.Read(buf, endianness, &number)

	var errorCode uint16
	binary.Read(buf, endianness, &errorCode)

	return MsgRegisterBetFailed{
		msgType:    MSG_TYPE_REGISTER_BET_FAILED,
		dni:        dni,
		number:     number,
		error_code: errorCode,
	}, nil
}
