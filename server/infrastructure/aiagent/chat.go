package aiagent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"github.com/factly/gopie/domain/models"
	"github.com/sashabaranov/go-openai"
	"go.uber.org/zap"
)

// Chat initiates a chat session with the AI agent using OpenAI's API
func (a *aiAgent) Chat(ctx context.Context, params *models.AIAgentChatParams) {
	// Convert messages to OpenAI format
	messages := make([]openai.ChatCompletionMessage, 0, len(params.Messages))
	for _, msg := range params.PrevMessages {
		messages = append(messages, openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		})
	}

	for _, msg := range params.Messages {
		messages = append(messages, openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		})
	}

	// Add metadata with project and dataset IDs if provided
	metadata := make(map[string]string)
	metadata["project_ids"] = params.ProjectIDs
	metadata["dataset_ids"] = params.DatasetIDs

	// Create the completion request
	req := openai.ChatCompletionRequest{
		Messages: messages,
		Stream:   true,
		Metadata: metadata,
	}

	// Create the stream
	stream, err := a.client.CreateChatCompletionStream(context.Background(), req)
	if err != nil {
		a.logger.Error("Error creating chat completion stream", zap.Error(err))
		params.ErrChan <- fmt.Errorf("error creating chat completion stream: %w", err)
		close(params.ErrChan)
		close(params.DataChan)
		return
	}
	defer stream.Close()

	// Process the stream
	for {
		resp, err := stream.Recv()
		if errors.Is(err, io.EOF) {
			// End of stream
			params.ErrChan <- io.EOF
			return
		}
		if err != nil {
			a.logger.Error("Error receiving stream response", zap.Error(err))
			params.ErrChan <- fmt.Errorf("error receiving stream response: %w", err)
			return
		}

		// Skip empty choices
		if len(resp.Choices) == 0 {
			continue
		}

		respData, err := json.Marshal(resp)
		if err != nil {
			a.logger.Error("Error marshaling response", zap.Error(err))
			continue
		}

		params.DataChan <- respData
	}
}
