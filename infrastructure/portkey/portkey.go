package portkey

import (
	"context"
	"net/http"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/sashabaranov/go-openai"
	"go.uber.org/zap"
)

type PortkeyClient struct {
	client *openai.Client
	model  string
	logger *logger.Logger
}

type defaultHeaderTransport struct {
	Origin http.RoundTripper
	Header http.Header
}

func (t *defaultHeaderTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	for key, values := range t.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}
	return t.Origin.RoundTrip(req)
}

// Create new portkey client from config
func NewPortKeyClient(cfg config.PortKeyConfig, logger *logger.Logger) repositories.AiRepository {

	// set portkey config in for request
	header := http.Header{}
	header.Set("x-portkey-virtual-key", cfg.VirtualKey)
	header.Set("x-portkey-api-key", cfg.Apikey)

	// create custom http client for portkey to work
	httpClient := &http.Client{
		Transport: &defaultHeaderTransport{
			Origin: http.DefaultTransport,
			Header: header,
		},
	}

	// X is used instead instead of an actual api_key because it is handled by portkey itself
	oaConfig := openai.DefaultConfig("X")
	oaConfig.HTTPClient = httpClient
	oaConfig.BaseURL = cfg.BaseUrl

	client := openai.NewClientWithConfig(oaConfig)
	model := cfg.AIModel
	logger.Info("Portkey client initialized", zap.String("model", model))
	return &PortkeyClient{client, model, logger}
}

func (c *PortkeyClient) GenerateSql(content string) (string, error) {
	c.logger.Debug("generating sql from portkey")
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	ctx := context.Background()

	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: []openai.ChatCompletionMessage{msgs},
		// Temperature: 0.2,
	})
	if err != nil {
		return "", err
	}

	if len(res.Choices) == 0 {
		return "", domain.ErrFailedToGenerateSql
	}
	c.logger.Debug("generated sql from portkey", zap.String("sql", res.Choices[0].Message.Content))
	return res.Choices[0].Message.Content, nil
}
