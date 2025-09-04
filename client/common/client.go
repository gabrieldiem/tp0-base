package common

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID             string
	ServerAddress  string
	BatchMaxAmount int
}

// Client manages sending bets to a server and receiving responses.
// It also listens for OS signals (SIGTERM, SIGINT) to stop execution..
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

// NewClient creates a Client with the given configuration and bet provider.
// It registers the client to listen for SIGTERM and SIGINT.
func NewClient(config ClientConfig, betProvider BetProvider) *Client {
	client := &Client{
		config:        config,
		signalChannel: make(chan os.Signal, MAX_SIGNAL_BUFFER),
		betProvider:   betProvider,
		protocol:      NewBetProtocol(config.ServerAddress, config.ID, config.BatchMaxAmount),
	}

	signal.Notify(client.signalChannel, syscall.SIGTERM, syscall.SIGINT)
	return client
}

// StartClientLoop runs the client loop.
// It initializes the protocol, sets up signal handling, and runs
// iterations while there are bets available and no stop condition.
func (c *Client) StartClientLoop() {
	loop := CONTINUE
	defer signal.Stop(c.signalChannel)
	defer c.flushLogs()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		sig := <-c.signalChannel
		log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
		cancel()
	}()

	var pendingBet *Bet = nil

	for loop == CONTINUE {
		err := c.protocol.Init()
		if err != nil {
			return
		}

		loop = c.processBatch(&pendingBet, ctx)
		c.resourceCleanup()

		if !c.betProvider.HasNextBet() {
			break
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) processBatch(pendingBet **Bet, ctx context.Context) int {
	canGroup := true
	var bets []Bet = []Bet{}
	var betsBatchSizeInBytes int = 0

	if *pendingBet != nil {
		bets = append(bets, **pendingBet)
		*pendingBet = nil
	}

	for c.betProvider.HasNextBet() && canGroup {
		bet, err := c.betProvider.NextBet()

		if err != nil {
			log.Criticalf("action: loop_finished | result: fail | error: %s", bet.Dni, bet.Number, err)
			return STOP
		}

		canGroup = c.protocol.CanGroupBet(len(bets), bet, &betsBatchSizeInBytes)

		if canGroup {
			bets = append(bets, *bet)
		} else {
			*pendingBet = bet
		}
	}

	if len(bets) > 0 {
		return c.sendBatch(&bets, betsBatchSizeInBytes, ctx)
	}

	return STOP
}

func (c *Client) sendBatch(bets *[]Bet, betsBatchSize int, ctx context.Context) int {
	err := c.protocol.RegisterBets(bets, betsBatchSize, ctx)
	if err != nil && err != ctx.Err() {
		log.Criticalf("action: apuesta_enviada | result: fail | cantidad: %v | error: %s", len(*bets), err)
		return STOP
	}

	if ctx.Err() != nil {
		return STOP
	}

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
