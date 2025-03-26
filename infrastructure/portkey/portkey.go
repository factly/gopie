package portkey

import (
	"context"
	"net/http"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
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
func NewPortKeyClient(cfg config.PortKeyConfig, logger *logger.Logger) *PortkeyClient {

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

func (c *PortkeyClient) GenerateResponse(content string) (string, error) {
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

func (c *PortkeyClient) GenerateChatResponseFunc(userMsg string, prevMsgs []*models.ChatMessage) (string, error) {
	c.logger.Debug("generating sql from portkey")
	msgs := make([]openai.ChatCompletionMessage, 0, len(prevMsgs)+1)
	for _, msg := range prevMsgs {
		if msg.Role == "assistant" || msg.Role == "user" {
			msgs = append(msgs, openai.ChatCompletionMessage{
				Role:    msg.Role,
				Content: msg.Content,
			})
		}
	}
	latestMessage := openai.ChatCompletionMessage{
		Role:    "user",
		Content: userMsg,
	}
	msgs = append(msgs, latestMessage)
	ctx := context.Background()
	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: msgs,
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

func (c *PortkeyClient) GenerateSql(content string) (string, error) {
	return c.GenerateResponse(content)
}

func (c *PortkeyClient) GenerateChatResponse(ctx context.Context, userMessage string, prevMessages []*models.ChatMessage) (*models.AiChatResponse, error) {
	resp, err := c.GenerateChatResponseFunc(userMessage, prevMessages)
	if err != nil {
		return nil, err
	}

	return &models.AiChatResponse{
		Response: resp,
	}, nil
}

func (c *PortkeyClient) GenerateTitle(ctx context.Context, content string) (*models.AiChatResponse, error) {
	systemPrompt := `
	!! IMPORTANT: In the response only provide the title of the content. Do not provide any other information. !!
		Generate a title for the following content:
	` + content

	resp, err := c.GenerateResponse(systemPrompt)
	if err != nil {
		return nil, err
	}

	return &models.AiChatResponse{
		Response: resp,
	}, nil
}
