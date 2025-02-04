package services

import "github.com/factly/gopie/application/repositories"

type AiDriver struct {
	ai repositories.AiRepository
}

func NewAiDriver(ai repositories.AiRepository) *AiDriver {
	return &AiDriver{ai}
}

func (d *AiDriver) GenerateSql(query string) (string, error) {
	return d.ai.GenerateSql(query)
}
