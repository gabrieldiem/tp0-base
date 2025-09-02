package common

import (
	"bytes"
	"encoding/binary"
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

type Bet struct {
	Name      string
	Surname   string
	Dni       int
	Birthdate time.Time
	Number    int
}

type BetProvider interface {
	NextBet() Bet
	HasNextBet() bool
}

type EnvBetProvider struct {
	bet     Bet
	hasNext bool
}

func NewEnvBetProvider() (*EnvBetProvider, error) {
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

	bet := Bet{
		Name:      os.Getenv(NAME_ENV_KEY),
		Surname:   os.Getenv(SURNAME_ENV_KEY),
		Dni:       dni,
		Birthdate: birthdate,
		Number:    num,
	}

	return &EnvBetProvider{
		bet:     bet,
		hasNext: true,
	}, nil
}

func (p *EnvBetProvider) NextBet() Bet {
	return p.bet
}

func (p *EnvBetProvider) HasNextBet() bool {
	if p.hasNext {
		p.hasNext = false
		return true
	}
	return false
}

/*
| len_name (4 bytes) | name (len_name bytes) | len_surname (4 bytes) | surname (len_surname bytes) |
| DNI (4 bytes) | birthdate (8 bytes) | number (4 bytes) |
*/
func (b Bet) ToBytes(endianness binary.ByteOrder) []byte {
	valueBuff := new(bytes.Buffer)

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
