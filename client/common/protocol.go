package common

import (
	"fmt"
)

type BetProtocol struct {
	id     string
	socket Socket
}

const (
	BET_NUMBER_FOR_ERRORS = -1
)

func NewBetProtocol(serverAddress string, id string) BetProtocol {
	return BetProtocol{
		id:     id,
		socket: NewSocket(serverAddress),
	}
}

// createClientSocket establishes a TCP connection to the configured
// server address. If the connection fails, the error is logged and
// returned. On success, the connection is stored in the client.
func (p *BetProtocol) Init() error {
	err := p.socket.Init()
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			p.id,
			err,
		)
		return err
	}

	return nil
}

func (p *BetProtocol) Cleanup() error {
	err := p.socket.Cleanup()
	if err != nil {
		log.Errorf("action: closing_socket | result: fail | client_id: %v | error: %s", p.id, err)
		return err
	}

	log.Infof("action: closing_socket | result: success | client_id: %v", p.id)
	return nil
}

func (p *BetProtocol) registerBet(bet *Bet) error {
	msg := NewMsgRegisterBet(*bet)
	err := p.socket.SendMessage(msg)
	return err
}

func (p *BetProtocol) expectRegisterBetOk(bet *Bet) (betNumber int, err error) {
	msg, err := p.socket.ReceiveMessage()
	if err != nil {
		return BET_NUMBER_FOR_ERRORS, err
	}

	switch msg.(type) {
	case MsgRegisterBetOk:
		return int(msg.(MsgRegisterBetOk).number), nil
	case MsgRegisterBetFailed:
		return BET_NUMBER_FOR_ERRORS, fmt.Errorf("Recevied MsgRegisterBetFailed")
	default:
		return BET_NUMBER_FOR_ERRORS, fmt.Errorf("Received unexpected message")
	}
}
