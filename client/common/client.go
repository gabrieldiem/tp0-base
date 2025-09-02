package common

import (
	"bufio"
	"fmt"
	"net"
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
	conn          net.Conn
	signalChannel chan os.Signal
	betProvider   BetProvider
	protocol      BetProtocol
}

const (
	// MESSAGE_DELIMITER defines the character used to delimit messages.
	MESSAGE_DELIMITER = '\n'

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
		protocol:      NewBetProtocol(),
	}

	signal.Notify(client.signalChannel, syscall.SIGTERM, syscall.SIGINT)
	return client
}

// createClientSocket establishes a TCP connection to the configured
// server address. If the connection fails, the error is logged and
// returned. On success, the connection is stored in the client.
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	c.conn = conn
	return nil
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

	// Create the connection the server in every loop iteration. Send an
	err := c.createClientSocket()
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
		return STOP
	}

	err = c.protocol.expectRegisterBetOk(bet)
	if err != nil {
		return STOP
	}

	return CONTINUE
}

// resourceCleanup closes the active TCP connection and logs the action.
func (c *Client) resourceCleanup() error {
	log.Infof("action: closing_socket | result: success | client_id: %v", c.config.ID)
	return c.conn.Close()
}

// sendMessage formats and sends a message to the server with the
// given message ID. The message format is:
//
//	[CLIENT <ID>] Message N°<msgID>\n
//
// Returns an error if the message cannot be sent.
func (c *Client) sendMessage(msgID int) error {
	msg := fmt.Sprintf("[CLIENT %v] Message N°%v%c", c.config.ID, msgID, MESSAGE_DELIMITER)
	err := c.sendAll(msg)
	if err != nil {
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	return nil
}

// receiveMessage reads a single message from the server until the
// MESSAGE_DELIMITER is encountered. Logs the received message or
// an error if reading fails.
func (c *Client) receiveMessage() error {
	msg, err := c.readAll()

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
		c.config.ID,
		msg,
	)
	return nil
}

// sendAll writes the entire message to the TCP connection, retrying
// until all bytes are sent or an error occurs.
func (c *Client) sendAll(msg string) error {
	data := []byte(msg)
	total := 0

	for total < len(data) {
		n, err := c.conn.Write(data[total:])
		if err != nil {
			return fmt.Errorf("failed to write to connection: %w", err)
		}
		total += n
	}
	return nil
}

// readAll reads from the TCP connection until MESSAGE_DELIMITER is
// encountered. Returns the message as a string
func (c *Client) readAll() (string, error) {
	return bufio.NewReader(c.conn).ReadString(MESSAGE_DELIMITER)
}

// Flushes any buffered data in stdout and stderr to ensure
// all logs are written.
func (c *Client) flushLogs() {
	os.Stdout.Sync()
	os.Stderr.Sync()
}
