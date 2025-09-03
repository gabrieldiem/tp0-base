package common

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
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
		protocol:      NewBetProtocol(config.ServerAddress, config.ID),
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

	err := c.protocol.Init()
	if err != nil {
		return
	}

	defer c.resourceCleanup()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		sig := <-c.signalChannel
		log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
		cancel()
	}()

	for c.betProvider.HasNextBet() && loop == CONTINUE {
		bet := c.betProvider.NextBet()
		loop = c.runIteration(&bet, ctx)
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

// runIteration sends a bet, waits for a response, and logs the result.
// It returns STOP if an error occurs, otherwise CONTINUE.
func (c *Client) runIteration(bet *Bet, ctx context.Context) int {
	err := c.protocol.registerBet(bet, ctx)
	if err != nil {
		log.Criticalf("action: apuesta_enviada | result: fail | dni: %v | numero: %v | error: %s", bet.Dni, bet.Number, err)
		return STOP
	}

	betNumber, err := c.protocol.expectRegisterBetOk(ctx)
	if err != nil && err != ctx.Err() {
		log.Criticalf("action: confirmacion_apuesta_enviada | result: fail | dni: %v | numero: %v | error: %s", bet.Dni, bet.Number, err)
		return STOP
	}

	if ctx.Err() != nil {
		return STOP
	}

	if bet.Number != betNumber {
		log.Criticalf(
			"action: confirmacion_apuesta_enviada | "+
				"result: fail | "+
				"dni: %v | "+
				"numero: %v | "+
				"error: confirmation is for different number expected %v but got %v",
			bet.Dni, bet.Number, bet.Number, betNumber,
		)
		return CONTINUE
	}

	log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v", bet.Dni, bet.Number)

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
