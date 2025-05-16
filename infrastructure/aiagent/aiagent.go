package aiagent

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
)

type aiAgent struct {
	url    string
	logger *logger.Logger
}

func NewAIAgent(url string, logger *logger.Logger) repositories.AIAgentRepository {
	return &aiAgent{
		url:    url,
		logger: logger,
	}
}

func (a *aiAgent) buildUrl(endpoint string) string {
	url := a.url + endpoint
	return url
}
