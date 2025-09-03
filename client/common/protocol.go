package common

import (
	"context"
	"fmt"
)

// BetProtocol manages communication with the server using a Socket.
// It provides methods to initialize and clean up the connection,
// send a bet, and wait for a response.
type BetProtocol struct {
	id     string
	socket Socket
}

const (
	// BET_NUMBER_FOR_ERRORS is returned when an error occurs
	// while waiting for a bet confirmation.
	BET_NUMBER_FOR_ERRORS = -1
)

// NewBetProtocol creates a new BetProtocol with the given server address and client id.
func NewBetProtocol(serverAddress string, id string) BetProtocol {
	return BetProtocol{
		id:     id,
		socket: NewSocket(serverAddress),
	}
}

// Init establishes a TCP connection to the configured server address.
// If the connection fails, the error is logged and returned.
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

// Cleanup closes the active socket connection.
// It logs whether the cleanup succeeded or failed.
func (p *BetProtocol) Cleanup() error {
	err := p.socket.Cleanup()
	if err != nil {
		log.Errorf("action: closing_socket | result: fail | client_id: %v | error: %s", p.id, err)
		return err
	}

	log.Infof("action: closing_socket | result: success | client_id: %v", p.id)
	return nil
}

// registerBet sends a bet to the server using the socket.
// It logs the action and returns any error from the socket.
func (p *BetProtocol) registerBet(bet *Bet, ctx context.Context) error {
	msg := NewMsgRegisterBet(*bet)
	log.Infof("action: registering_bet | result: in_progress | bet: %v", bet)
	err := p.socket.SendMessage(msg, ctx)
	return err
}

// expectRegisterBetOk waits for a response from the server.
// It returns the confirmed bet number if a MsgRegisterBetOk is received.
// If a MsgRegisterBetFailed or an unexpected message is received,
// it returns BET_NUMBER_FOR_ERRORS and an error.
func (p *BetProtocol) expectRegisterBetOk(ctx context.Context) (betNumber int, err error) {
	msg, err := p.socket.ReceiveMessage(ctx)
	if err != nil {
		return BET_NUMBER_FOR_ERRORS, err
	}

	switch message := msg.(type) {
	case MsgRegisterBetOk:
		return int(message.number), nil
	case MsgRegisterBetFailed:
		return int(message.number), fmt.Errorf("recevied MsgRegisterBetFailed")
	default:
		return BET_NUMBER_FOR_ERRORS, fmt.Errorf("received unexpected message")
	}
}
