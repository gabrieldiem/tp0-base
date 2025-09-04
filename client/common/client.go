package common

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig holds the configuration parameters for a client instance.
// - ID: unique identifier of the client.
// - ServerAddress: address of the server to connect to.
// - BatchMaxAmount: maximum number of bets that can be grouped in a single batch.
type ClientConfig struct {
	ID             string
	ServerAddress  string
	BatchMaxAmount int
}

// Client manages sending bets to a server and receiving responses.
// It also listens for OS signals (SIGTERM, SIGINT) to stop execution gracefully.
type Client struct {
	config        ClientConfig
	signalChannel chan os.Signal
	betProvider   BetProvider
	protocol      BetProtocol
}

const (
	// CONTINUE indicates that the client loop should continue.
	CONTINUE = 0

	// STOP indicates that the client loop should stop.
	STOP = 1

	// MAX_SIGNAL_BUFFER is the buffer size for the signal channel.
	MAX_SIGNAL_BUFFER = 5
)

// NewClient creates a new Client with the given configuration and bet provider.
// It also registers the client to listen for SIGTERM and SIGINT signals
// so that it can gracefully stop when the process is terminated.
func NewClient(config ClientConfig, betProvider BetProvider) *Client {
	client := &Client{
		config:        config,
		signalChannel: make(chan os.Signal, MAX_SIGNAL_BUFFER),
		betProvider:   betProvider,
		protocol:      NewBetProtocol(config.ServerAddress, config.ID, config.BatchMaxAmount),
	}

	// Subscribe to OS termination signals
	signal.Notify(client.signalChannel, syscall.SIGTERM, syscall.SIGINT)
	return client
}

// StartClientLoop runs the main client loop.
// It initializes the protocol, sets up signal handling, and processes bets
// in batches until there are no more bets or a stop condition occurs.
func (c *Client) StartClientLoop() {
	loop := CONTINUE
	defer signal.Stop(c.signalChannel)
	defer c.flushLogs()

	// Context used for cancellation when a signal is received
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Goroutine to listen for OS signals and cancel the context
	go func() {
		sig := <-c.signalChannel
		log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
		cancel()
	}()

	// pendingBet stores a bet that could not fit in the last batch
	var pendingBet *Bet = nil

	for loop == CONTINUE {
		err := c.protocol.Init()
		if err != nil {
			return
		}

		loop = c.processBatch(&pendingBet, ctx)
		c.resourceCleanup()

		// Stop if no more bets are available
		if !c.betProvider.HasNextBet() {
			break
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

// processBatch groups bets into a batch (up to the configured max size)
// and sends them to the server. If a bet does not fit, it is stored
// in pendingBet for the next iteration.
func (c *Client) processBatch(pendingBet **Bet, ctx context.Context) int {
	canGroup := true
	var bets []Bet = []Bet{}
	var betsBatchSizeInBytes int = 0

	// If there was a leftover bet from the previous batch, start with it
	if *pendingBet != nil {
		bets = append(bets, **pendingBet)
		*pendingBet = nil
	}

	// Keep adding bets until we reach the batch limit or run out of bets
	for c.betProvider.HasNextBet() && canGroup {
		bet, err := c.betProvider.NextBet()

		if err != nil {
			log.Criticalf("action: loop_finished | result: fail | error: %s", bet.Dni, bet.Number, err)
			return STOP
		}

		// Check if the bet can be grouped into the current batch
		canGroup = c.protocol.CanGroupBet(len(bets), bet, &betsBatchSizeInBytes)

		if canGroup {
			bets = append(bets, *bet)
		} else {
			// Save bet for the next batch
			*pendingBet = bet
		}
	}

	// If we have bets, send them as a batch
	if len(bets) > 0 {
		return c.sendBatch(&bets, betsBatchSizeInBytes, ctx)
	}

	return STOP
}

// sendBatch sends a batch of bets to the server and waits for confirmation.
// It returns CONTINUE if successful, STOP otherwise.
func (c *Client) sendBatch(bets *[]Bet, betsBatchSize int, ctx context.Context) int {
	// Send the batch
	err := c.protocol.RegisterBets(bets, betsBatchSize, ctx)
	if err != nil && err != ctx.Err() {
		log.Criticalf("action: apuesta_enviada | result: fail | cantidad: %v | error: %s", len(*bets), err)
		return STOP
	}

	// Stop if context was cancelled (signal received)
	if ctx.Err() != nil {
		return STOP
	}

	// Wait for server confirmation
	err = c.protocol.ExpectRegisterBetOk(ctx)
	if err != nil && err != ctx.Err() {
		log.Criticalf("action: confirmacion_apuesta_enviada | result: fail | cantidad: %v | error: %s", len(*bets), err)
		return STOP
	}

	if ctx.Err() != nil {
		return STOP
	}

	log.Infof("action: apuesta_enviada | result: success | cantidad: %v", len(*bets))

	return CONTINUE
}

// resourceCleanup closes the active TCP connection and logs the action.
func (c *Client) resourceCleanup() error {
	return c.protocol.Cleanup()
}

// Flushes any buffered data in stdout and stderr to ensure
// all logs are written.
func (c *Client) flushLogs() {
	os.Stdout.Sync()
	os.Stderr.Sync()
}
