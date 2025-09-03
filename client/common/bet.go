package common

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"strconv"
	"time"
)

const (
	NAME_ENV_KEY      = "NOMBRE"
	SURNAME_ENV_KEY   = "APELLIDO"
	DNI_ENV_KEY       = "DOCUMENTO"
	BIRTHDATE_ENV_KEY = "NACIMIENTO"
	NUMBER_ENV_KEY    = "NUMERO"

	BIRTHDATE_FORMAT = "2006-01-02"
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

// BetProvider defines an interface for providing bets.
type BetProvider interface {
	NextBet() Bet
	HasNextBet() bool
}

// EnvBetProvider provides a single Bet from environment variables.
type EnvBetProvider struct {
	bet     Bet
	hasNext bool
}

// NewEnvBetProvider creates a new EnvBetProvider.
//
// It reads values from environment variables:
//   - NOMBRE
//   - APELLIDO
//   - DOCUMENTO
//   - NACIMIENTO (YYYY-MM-DD)
//   - NUMERO
//
// Returns an EnvBetProvider containing one Bet
func NewEnvBetProvider(agencyId int) (*EnvBetProvider, error) {
	dniStr := os.Getenv(DNI_ENV_KEY)
	dni, err := strconv.Atoi(dniStr)
	if err != nil {
		return nil, err
	}

	numStr := os.Getenv(NUMBER_ENV_KEY)
	num, err := strconv.Atoi(numStr)
	if err != nil {
		return nil, err
	}

	birthStr := os.Getenv(BIRTHDATE_ENV_KEY)
	birthdate, err := time.Parse(BIRTHDATE_FORMAT, birthStr)
	if err != nil {
		return nil, err
	}

	bet := NewBet(agencyId, os.Getenv(NAME_ENV_KEY), os.Getenv(SURNAME_ENV_KEY), dni, birthdate, num)

	return &EnvBetProvider{
		bet:     bet,
		hasNext: true,
	}, nil
}

// NextBet returns the stored Bet.
func (p *EnvBetProvider) NextBet() Bet {
	return p.bet
}

// HasNextBet returns true the first time it is called, then false.
func (p *EnvBetProvider) HasNextBet() bool {
	if p.hasNext {
		p.hasNext = false
		return true
	}
	return false
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
