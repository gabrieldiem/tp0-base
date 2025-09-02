package common

import (
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

// Client Entity that encapsulates how
// It also handles OS signals (SIGTERM, SIGINT) to gracefully
// stop execution.
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

	// MAX_SIGNAL_BUFFER defines the buffer size for the signal channel.
	MAX_SIGNAL_BUFFER = 5
)

// NewClient creates and initializes a new Client instance using the
// provided configuration. It also registers the client to listen for
// SIGTERM and SIGINT signals to allow graceful shutdown.
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

// StartClientLoop runs the main client loop. It sends messages to the
// server periodically until either:
//   - The configured LoopAmount is reached.
//   - An OS signal (SIGTERM, SIGINT) is received.
//   - A critical error occurs while sending/receiving messages.
//
// Each iteration establishes a new TCP connection, sends a message,
// waits for a response, and then sleeps for LoopPeriod before the
// next iteration.
func (c *Client) StartClientLoop() {
	// There is an autoincremental msgID to identify every message sent
	loop := CONTINUE
	defer signal.Stop(c.signalChannel)
	defer c.flushLogs()

	err := c.protocol.Init()
	if err != nil {
		return
	}

	defer c.resourceCleanup()

	for c.betProvider.HasNextBet() && loop == CONTINUE {
		select {
		case sig := <-c.signalChannel:
			log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
			return
		default:
			bet := c.betProvider.NextBet()
			loop = c.runIteration(&bet)
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

// runIteration executes a single client loop iteration:
//  1. Establishes a TCP connection.
//  2. Sends a message with the current message ID.
//  3. Waits for and logs the server response.
//  4. Sleeps for LoopPeriod before the next iteration.
//
// Returns STOP if a critical error occurs or a signal is received,
// otherwise CONTINUE
func (c *Client) runIteration(bet *Bet) int {
	err := c.protocol.registerBet(bet)
	if err != nil {
		log.Criticalf("action: apuesta_enviada | result: fail | dni: %v | numero: %v | error: %s", bet.Dni, bet.Number, err)
		return STOP
	}

	betNumber, err := c.protocol.expectRegisterBetOk(bet)
	if err != nil {
		log.Criticalf("action: confirmacion_apuesta_enviada | result: fail | dni: %v | numero: %v | error: %s", bet.Dni, bet.Number, err)
		return STOP
	}

	if bet.Number != betNumber {
		log.Criticalf("action: confirmacion_apuesta_enviada | result: fail | dni: %v | numero: %v | error: confirmation is for different number", bet.Dni, bet.Number)
	}

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
