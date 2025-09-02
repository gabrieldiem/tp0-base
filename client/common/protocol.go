package common

type BetProtocol struct {
}

func NewBetProtocol() BetProtocol {
	return BetProtocol{}
}

func (p *BetProtocol) registerBet(bet *Bet) error {
	return nil
}

func (p *BetProtocol) expectRegisterBetOk(bet *Bet) error {
	return nil
}
