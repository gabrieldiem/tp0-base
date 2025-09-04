package common

import (
	"context"
	"fmt"
)

// BetProtocol manages communication with the server using a Socket.
// It provides methods to initialize and clean up the connection,
// send batches of bets, and wait for server confirmations.
type BetProtocol struct {
	id             string // client identifier
	socket         Socket // underlying TCP socket abstraction
	batchMaxAmount int    // maximum number of bets allowed in a batch
}

const (
	// Number of bytes in a kilobyte.
	KILO_BYTE = 1024

	// MAX_BETS_BATCH_SIZE is the maximum allowed size of a batch in bytes.
	MAX_BETS_BATCH_SIZE = 8 * KILO_BYTE
)

// NewBetProtocol creates a new BetProtocol with the given server address,
// client ID, and maximum batch size. The TCP connection is not established
// until Init() is called.
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

// RegisterBets sends a batch of bets to the server.
// It logs the number of bets and the packet size in KB before sending.
// The packet size includes both the serialized bets and protocol overhead.
func (p *BetProtocol) RegisterBets(bets *[]Bet, betsBatchSize int, ctx context.Context) error {
	msg := NewMsgRegisterBets(*bets)

	// Compute packet size in KB (bets + protocol overhead)
	packetSizeKB := float64(betsBatchSize+GetOverheadInBytes(len(*bets)+1)) / float64(KILO_BYTE)

	log.Infof(
		"action: registering_bet | result: in_progress | number_of_bets: %v | packet_size: %.2fKB",
		len(*bets),
		packetSizeKB,
	)

	err := p.socket.SendMessage(msg, ctx)
	return err
}

// SendAck sends an ACK message to the server to confirm
// that the previous message was received.
func (p *BetProtocol) SendAck(ctx context.Context) error {
	log.Infof("action: sending_ack | result: in_progress")
	return p.socket.SendMessage(NewMsgAck(), ctx)
}

// SendAllBetsSent notifies the server that the client has finished
// sending all bets.
func (p *BetProtocol) SendAllBetsSent(ctx context.Context) error {
	log.Infof("action: sending_all_bets_sent | result: in_progress")
	return p.socket.SendMessage(NewMsgAllBetsSent(), ctx)
}

// SendRequestWinners asks the server to send the list of winning bets.
func (p *BetProtocol) SendRequestWinners(ctx context.Context) error {
	log.Infof("action: consulta_ganadores | result: in_progress")
	return p.socket.SendMessage(NewMsgRequestWinners(), ctx)
}

// CanGroupBet checks if adding `bet` to the current batch of bets
// would keep the total binary size under the maximum allowed batch size (8KB).
//
// - numberOfBets: current number of bets in the batch
// - bet: the new bet to consider adding
// - betsBatchSize: pointer to the current accumulated batch size in bytes
//
// Returns true if the bet can be added without exceeding the limit.
// If true, betsBatchSize is updated to include the new bet's size.
func (p *BetProtocol) CanGroupBet(numberOfBets int, bet *Bet, betsBatchSize *int) bool {
	// Check if adding another bet would exceed the configured max amount
	if numberOfBets+1 > p.batchMaxAmount {
		return false
	}

	// Compute size of the new bet in bytes
	newBetSize := len(bet.ToBytes(NETWORK_ENDIANNESS))

	// Compute new total size including protocol overhead
	newTotalSize := *betsBatchSize + newBetSize + GetOverheadInBytes(numberOfBets+1)

	// Check if the new total size fits within the 8KB limit
	canGroup := newTotalSize <= MAX_BETS_BATCH_SIZE

	// If it fits, update the accumulated batch size
	if canGroup {
		*betsBatchSize += newBetSize
	}

	return canGroup
}

// ExpectRegisterBetOk waits for a response from the server after sending a batch.
// It expects either:
//   - MsgRegisterBetOk → success
//   - MsgRegisterBetFailed → failure
//   - Any other message → treated as unexpected
//
// Returns nil if the confirmation is successful, or an error otherwise.
func (p *BetProtocol) ExpectRegisterBetOk(ctx context.Context) error {
	msg, err := p.socket.ReceiveMessage(ctx)
	if err != nil {
		return err
	}

	switch msg.(type) {
	case MsgRegisterBetOk:
		// Server confirmed batch registration
		return nil
	case MsgRegisterBetFailed:
		// Server explicitly rejected the batch
		return fmt.Errorf("received MsgRegisterBetFailed")
	default:
		// Unexpected message type
		return fmt.Errorf("received unexpected message")
	}
}

// ExpectWinners waits for the server to send the list of winners.
// It expects a MsgInformWinners message containing the list of DNI winners.
// Returns the list of winners or an error if the message type is unexpected.
func (p *BetProtocol) ExpectWinners(ctx context.Context) ([]uint32, error) {
	msg, err := p.socket.ReceiveMessage(ctx)
	if err != nil {
		return nil, err
	}

	switch m := msg.(type) {
	case MsgInformWinners:
		// Return the list of winners received from the server
		return m.DniWinners, nil
	default:
		// Unexpected message type
		return nil, fmt.Errorf("received unexpected message")
	}
}
