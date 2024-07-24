package ai

import (
	"context"
	"errors"
	"log"
	"net/http"

	"github.com/mitchellh/mapstructure"
	"github.com/sashabaranov/go-openai"
)

type PortKeyClient struct {
	client *openai.Client
	model  string
}

type config struct {
	VirtualKey string `mapstructure:"portkey_virtual_key"`
	PKApikey   string `mapstructure:"portkey_api_key"`
	PKBaseUrl  string `mapstructure:"portkey_base_url"`
	AIModel    string `mapstructure:"ai_model"`
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
func NewPortKeyClient(cfg map[string]any) *PortKeyClient {

	// destructure the config
	config := &config{}
	err := mapstructure.Decode(cfg, config)
	if err != nil {
		log.Println("error create portkey: ", err.Error())
		return nil
	}

	// set portkey config in for request
	header := http.Header{}
	header.Set("x-portkey-virtual-key", config.VirtualKey)
	header.Set("x-portkey-api-key", config.PKApikey)

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
	oaConfig.BaseURL = config.PKBaseUrl

	client := openai.NewClientWithConfig(oaConfig)
	model := config.AIModel
	return &PortKeyClient{client, model}
}

func (c *PortKeyClient) Complete(ctx context.Context, content string) (map[string]string, error) {
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:       c.model,
		Messages:    []openai.ChatCompletionMessage{msgs},
		Temperature: 0.2,
	})
	if err != nil {
		return nil, err
	}

	if len(res.Choices) == 0 {
		return nil, errors.New("no choices returned")
	}
	return map[string]string{
		"sql": res.Choices[0].Message.Content,
	}, nil
}
