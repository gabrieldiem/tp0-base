package common

const (
	MSG_TYPE_REGISTER_BET        = 1
	MSG_TYPE_REGISTER_BET_OK     = 2
	MSG_TYPE_REGISTER_BET_FAILED = 3
)

type Message interface {
	ToBytes() []byte
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
func (msg MsgRegisterBet) ToBytes() []byte {
	return []byte{}
}

func (msg MsgRegisterBetOk) ToBytes() []byte {
	return []byte{}
}

func (msg MsgRegisterBetFailed) ToBytes() []byte {
	return []byte{}
}
