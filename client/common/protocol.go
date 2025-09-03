package common

import (
	"context"
	"fmt"
)

// BetProtocol manages communication with the server using a Socket.
// It provides methods to initialize and clean up the connection,
// send a bet, and wait for a response.
type BetProtocol struct {
	id             string
	socket         Socket
	batchMaxAmount int
}

const (
	// BET_NUMBER_FOR_ERRORS is returned when an error occurs
	// while waiting for a bet confirmation.
	BET_NUMBER_FOR_ERRORS = -1

	KILO_BYTE           = 1024
	MAX_BETS_BATCH_SIZE = 8 * KILO_BYTE
)

// NewBetProtocol creates a new BetProtocol with the given server address and client id.
func NewBetProtocol(serverAddress string, id string, batchMaxAmount int) BetProtocol {
	return BetProtocol{
		id:             id,
		socket:         NewSocket(serverAddress),
		batchMaxAmount: batchMaxAmount,
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

func (p *BetProtocol) RegisterBets(bets *[]Bet, betsBatchSize int, ctx context.Context) error {
	msg := NewMsgRegisterBets(*bets)

	packetSizeKB := float64(betsBatchSize+GetOverheadInBytes(len(*bets)+1)) / float64(KILO_BYTE)

	log.Infof(
		"action: registering_bet | result: in_progress | number_of_bets: %v | packet_size: %.2fKB",
		len(*bets),
		packetSizeKB,
	)

	err := p.socket.SendMessage(msg, ctx)
	return err
}

// CanGroupBet checks if adding `bet` to the current batch of bets
// would keep the total binary size under 8KB.
func (p *BetProtocol) CanGroupBet(numberOfBets int, bet *Bet, betsBatchSize *int) bool {
	if numberOfBets+1 > p.batchMaxAmount {
		return false
	}

	newBetSize := len(bet.ToBytes(NETWORK_ENDIANNESS))
	newTotalSize := *betsBatchSize + newBetSize + GetOverheadInBytes(numberOfBets+1)

	canGroup := newTotalSize <= MAX_BETS_BATCH_SIZE

	if canGroup {
		*betsBatchSize += newBetSize
	}

	return canGroup
}

// expectRegisterBetOk waits for a response from the server.
// It returns the confirmed bet number if a MsgRegisterBetOk is received.
// If a MsgRegisterBetFailed or an unexpected message is received,
// it returns BET_NUMBER_FOR_ERRORS and an error.
func (p *BetProtocol) ExpectRegisterBetOk(ctx context.Context) error {
	msg, err := p.socket.ReceiveMessage(ctx)

	if err != nil {
		return err
	}

	switch msg.(type) {
	case MsgRegisterBetOk:
		return nil
	case MsgRegisterBetFailed:
		return fmt.Errorf("recevied MsgRegisterBetFailed")
	default:
		return fmt.Errorf("received unexpected message")
	}
}
