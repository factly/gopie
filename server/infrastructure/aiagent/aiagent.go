package aiagent

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/sashabaranov/go-openai"
	"go.uber.org/zap"
)

type aiAgent struct {
	url    string
	logger *logger.Logger
	client *openai.Client
}

func NewAIAgent(url string, logger *logger.Logger) repositories.AIAgentRepository {
	// Create OpenAI client
	config := openai.DefaultConfig("X")
	config.BaseURL = url + "/api/v1"
	client := openai.NewClientWithConfig(config)
	if client == nil {
		logger.Fatal("Failed to create OpenAI client")
	}

	logger.Info("OpenAI client created successfully", zap.String("url", url))

	return &aiAgent{
		url:    url,
		logger: logger,
		client: client,
	}
}

func (a *aiAgent) buildUrl(endpoint string) string {
	url := a.url + endpoint
	return url
}
