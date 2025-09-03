package common

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	CSV_NAME_ROW_KEY      = 0
	CSV_SURNAME_ROW_KEY   = 1
	CSV_DNI_ROW_KEY       = 2
	CSV_BIRTHDATE_ROW_KEY = 3
	CSV_NUMBER_ROW_KEY    = 4

	BIRTHDATE_FORMAT = "2006-01-02"

	CSV_FILEPATH        = "./agency.csv"
	CSV_SEPARATING_CHAR = ","
	CSV_FIELDS_COUNT    = 5
)

// Bet represents a bet with identifying information.
type Bet struct {
	Agency    int
	Name      string
	Surname   string
	Dni       int
	Birthdate time.Time
	Number    int
}

// NewBet creates a new Bet with the given values.
func NewBet(agency int, name, surname string, dni int, birthdate time.Time, number int) Bet {
	return Bet{
		Agency:    agency,
		Name:      name,
		Surname:   surname,
		Dni:       dni,
		Birthdate: birthdate,
		Number:    number,
	}
}

/*
ToBytes serializes a Bet into binary format:

| agency (4 bytes) |
| name_len (4 bytes) | name (name_len bytes) |
| surname_len (4 bytes) | surname (surname_len bytes) |
| dni (4 bytes) |
| birthdate (8 bytes, Unix timestamp) |
| number (4 bytes) |
*/
func (b Bet) ToBytes(endianness binary.ByteOrder) []byte {
	valueBuff := new(bytes.Buffer)

	binary.Write(valueBuff, endianness, uint32(b.Agency))

	// Name encoding
	nameBytes := []byte(b.Name)
	binary.Write(valueBuff, endianness, uint32(len(nameBytes)))
	valueBuff.Write(nameBytes)

	// Surname encoding
	surnameBytes := []byte(b.Surname)
	binary.Write(valueBuff, endianness, uint32(len(surnameBytes)))
	valueBuff.Write(surnameBytes)

	// Dni encoding
	binary.Write(valueBuff, endianness, uint32(b.Dni))

	// Birthdate as Unix timestamp encoding
	binary.Write(valueBuff, endianness, b.Birthdate.Unix())

	// Number encoding
	binary.Write(valueBuff, endianness, uint32(b.Number))

	return valueBuff.Bytes()
}

// String returns a string representation of the Bet.
func (b Bet) String() string {
	return fmt.Sprintf(
		"Bet(Name=%s, Surname=%s, Dni=%d, Birthdate=%s, Number=%d)",
		b.Name, b.Surname, b.Dni, b.Birthdate.Format(BIRTHDATE_FORMAT), b.Number,
	)
}

// BetProvider defines an interface for providing bets.
type BetProvider interface {
	NextBet() (*Bet, error)
	HasNextBet() bool
}

// EnvBetProvider provides a single Bet from environment variables.
type CsvBetProvider struct {
	agencyID   int
	file       *os.File
	scanner    *bufio.Scanner
	nextBet    *Bet
	nextBetErr error
	eof        bool
}

// NewCsvBetProvider opens the CSV file and prepares a streaming reader.
func NewCsvBetProvider(clientId int) (*CsvBetProvider, error) {
	file, err := os.Open(CSV_FILEPATH)
	if err != nil {
		return nil, fmt.Errorf("failed to open CSV file: %w", err)
	}

	scanner := bufio.NewScanner(file)

	provider := &CsvBetProvider{
		agencyID:   clientId,
		file:       file,
		scanner:    scanner,
		nextBet:    nil,
		nextBetErr: nil,
		eof:        false,
	}

	// Preload the first bet
	if err := provider.loadNext(); err != nil {
		provider.Close()
		return nil, err
	}

	return provider, nil
}

// loadNext advances the scanner, reads the next line, parses it into a Bet,
// and stores it in p.nextBet. If EOF is reached, it marks the provider as done.
func (p *CsvBetProvider) loadNext() error {
	if p.eof {
		return nil
	}

	// Read the next non-empty line from the CSV
	line, err := p.readNextLine()
	if err == io.EOF {
		// No more lines → mark as finished
		p.eof = true
		p.nextBet = nil
		return nil
	}

	if err != nil {
		return err
	}

	// Parse the line into a Bet
	bet, err := p.parseLine(line)
	if err != nil {
		return err
	}

	// Store the parsed bet for retrieval
	p.nextBet = &bet
	return nil
}

// readNextLine advances the scanner until it finds a non-empty line.
// Returns io.EOF when no more lines are available.
func (p *CsvBetProvider) readNextLine() (string, error) {
	for {
		keepReading := p.scanner.Scan()
		if !keepReading {
			// Scanner finished → check for errors
			if err := p.scanner.Err(); err != nil && err != io.EOF {
				return "", fmt.Errorf("error reading CSV: %w", err)
			}
			return "", io.EOF
		}

		// Trim whitespace around the line
		line := strings.TrimSpace(p.scanner.Text())
		if line == "" {
			// Skip empty lines and keep scanning
			continue
		}
		return line, nil
	}
}

// parseLine takes a raw CSV line (comma-separated string) and converts it
// into a Bet struct. It validates and parses each field individually.
func (p *CsvBetProvider) parseLine(line string) (Bet, error) {
	// Split the line into fields
	row_split := strings.Split(line, CSV_SEPARATING_CHAR)
	if len(row_split) < CSV_FIELDS_COUNT {
		return Bet{}, fmt.Errorf("invalid row: %q", line)
	}

	// Extract and clean name
	name := strings.TrimSpace(row_split[CSV_NAME_ROW_KEY])

	// Extract and clean surname
	surname := strings.TrimSpace(row_split[CSV_SURNAME_ROW_KEY])

	// Parse DNI
	dni, err := strconv.Atoi(strings.TrimSpace(row_split[CSV_DNI_ROW_KEY]))
	if err != nil {
		return Bet{}, fmt.Errorf("invalid DNI in row: %q, err: %w", line, err)
	}

	// Parse birthdate
	birthdate, err := time.Parse(BIRTHDATE_FORMAT, strings.TrimSpace(row_split[CSV_BIRTHDATE_ROW_KEY]))
	if err != nil {
		return Bet{}, fmt.Errorf("invalid birthdate in row: %q, err: %w", line, err)
	}

	// Parse bet number
	number, err := strconv.Atoi(strings.TrimSpace(row_split[CSV_NUMBER_ROW_KEY]))
	if err != nil {
		return Bet{}, fmt.Errorf("invalid number in row: %q, err: %w", line, err)
	}

	// Construct and return the Bet
	return NewBet(p.agencyID, name, surname, dni, birthdate, number), nil
}

// NextBet returns the current bet and advances to the next one.
func (p *CsvBetProvider) NextBet() (*Bet, error) {
	if p.nextBet == nil {
		return nil, p.nextBetErr
	}

	bet := *p.nextBet
	p.nextBetErr = p.loadNext() // preload next bet
	return &bet, nil
}

// HasNextBet returns true if there is another bet available.
func (p *CsvBetProvider) HasNextBet() bool {
	return p.nextBet != nil
}

// Close releases the file handle.
func (p *CsvBetProvider) Close() error {
	return p.file.Close()
}
