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
type Client struct {
	config        ClientConfig
	conn          net.Conn
	signalChannel chan os.Signal
}

const (
	MESSAGE_DELIMITER = '\n'
	CONTINUE          = 0
	STOP              = 1
	MAX_SIGNAL_BUFFER = 5
)

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config:        config,
		signalChannel: make(chan os.Signal, MAX_SIGNAL_BUFFER),
	}

	signal.Notify(client.signalChannel, syscall.SIGTERM, syscall.SIGINT)
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
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

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	result := CONTINUE
	defer signal.Stop(c.signalChannel)

	for msgID := 1; msgID <= c.config.LoopAmount && result == CONTINUE; msgID++ {
		select {
		case sig := <-c.signalChannel:
			log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
			return
		default:
			result = c.runIteration(msgID)
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) runIteration(msgID int) int {
	// Create the connection the server in every loop iteration. Send an
	err := c.createClientSocket()
	if err != nil {
		return CONTINUE
	}

	defer c.resourceCleanup()

	err = c.sendMessage(msgID)
	if err != nil {
		return STOP
	}

	err = c.receiveMessage()
	if err != nil {
		return STOP
	}

	// Wait a time between sending one message and the next one
	select {
	case sig := <-c.signalChannel:
		log.Infof("action: signal_%v_received | result: success | client_id: %v", sig, c.config.ID)
		return STOP
	case <-time.After(c.config.LoopPeriod):
		return CONTINUE
	}
}

func (c *Client) resourceCleanup() error {
	log.Infof("action: closing_socket | result: success | client_id: %v", c.config.ID)
	return c.conn.Close()
}

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

func (c *Client) readAll() (string, error) {
	return bufio.NewReader(c.conn).ReadString(MESSAGE_DELIMITER)
}
