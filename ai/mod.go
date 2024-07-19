package ai

import (
	"context"
	"errors"

	"github.com/sashabaranov/go-openai"
)

type OpenAI struct {
	client *openai.Client
}

func NewOpenAIClient(apiKey string) *OpenAI {
	client := openai.NewClient(apiKey)
	return &OpenAI{client}
}

func (c *OpenAI) Complete(ctx context.Context, content string) (map[string]string, error) {
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:       "gpt-4o-mini",
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
