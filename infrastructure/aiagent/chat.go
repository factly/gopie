package aiagent

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/factly/gopie/domain/models"
	"go.uber.org/zap"
)

// Chat initiates a chat session with the AI agent
func (a *aiAgent) Chat(ctx context.Context, params *models.AIAgentChatParams) {
	url := a.buildUrl("/api/v1/query")

	reqBody := map[string]any{
		"project_ids": params.ProjectIDs,
		"dataset_ids": params.DatasetIDs,
		"messages": []map[string]any{
			{
				"role":    "user",
				"content": params.UserInput,
			},
		},
	}

	reqBodyBuf, _ := json.Marshal(reqBody)

	req, err := http.NewRequest(http.MethodPost, url, bytes.NewBuffer(reqBodyBuf))
	if err != nil {
		a.logger.Error("Error in creating request to AI agent", zap.Error(err))
		params.ErrChan <- err
		close(params.ErrChan)
		close(params.DataChan)
		return
	}

	req.Header.Set("Content-Type", "application/json")

	httpClient := &http.Client{}

	resp, err := httpClient.Do(req)
	if err != nil {
		a.logger.Error("Error in sending request to AI agent", zap.Error(err))
		params.ErrChan <- err
		close(params.ErrChan)
		close(params.DataChan)
		return
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		a.logger.Error("Error in response from AI agent", zap.Int("status_code", resp.StatusCode))

		params.ErrChan <- fmt.Errorf("error in response from AI agent: %s", resp.Status)
		close(params.ErrChan)
		close(params.DataChan)
		return
	}
	if resp.Body == nil {
		a.logger.Error("Error in response body from AI agent", zap.Int("status_code", resp.StatusCode))

		params.ErrChan <- fmt.Errorf("error in response body from AI agent: %s", resp.Status)
		close(params.ErrChan)
		close(params.DataChan)
		return
	}

	a.handleChatStream(ctx, resp.Body, params.DataChan, params.ErrChan)
	return
}

// handleChatStream processes the streaming response from the AI agent
func (a *aiAgent) handleChatStream(_ context.Context, body io.ReadCloser, dataChan chan<- []byte, errChan chan<- error) {
	defer close(dataChan)
	defer close(errChan)

	scanner := bufio.NewScanner(body)
	// Set a reasonable buffer size based on expected message size
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	lastMessageTime := time.Now()

	for scanner.Scan() {
		select {
		default:
			now := time.Now()
			timeSinceLastMessage := now.Sub(lastMessageTime)
			lastMessageTime = now

			line := bytes.TrimSpace(scanner.Bytes())
			// ignore empty lines
			if len(line) == 0 {
				continue
			}

			// remove data: prefix
			line = bytes.TrimPrefix(line, []byte("data: "))

			var partialResponse SSEEvent
			if err := json.Unmarshal(line, &partialResponse); err != nil {
				a.logger.Error("Error in unmarshalling SSE event", zap.Error(err))
				errChan <- err
				return
			}

			if partialResponse.Error != nil {
				if partialResponse.Error.Message != "" {
					a.logger.Error("Error in SSE event", zap.String("error", partialResponse.Error.Message))
					errChan <- fmt.Errorf("error in SSE event: %s", partialResponse.Error)
				} else {
					a.logger.Error("Error in SSE event", zap.Any("error", errors.New("unknown error")))
					errChan <- fmt.Errorf("error in SSE event: %v", errors.New("unknown error"))
				}
				return
			}

			a.logger.Debug("Received SSE event",
				zap.String("event_node", partialResponse.ChatID),
				zap.String("status", partialResponse.TraceID),
				zap.String("message", partialResponse.Message.Content),
				zap.Duration("time_since_last_message", timeSinceLastMessage))

			dataChan <- line
		}
	}

	if err := scanner.Err(); err != nil {
		a.logger.Error("Error in scanning SSE event", zap.Error(err))
		errChan <- err
		return
	}

	errChan <- io.EOF
}
