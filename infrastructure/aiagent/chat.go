package aiagent

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/factly/gopie/domain/models"
	"go.uber.org/zap"
)

// Chat initiates a chat session with the AI agent
func (a *aiAgent) Chat(ctx context.Context, params *models.AIAgentChatParams) {
	url := a.buildUrl("/chat", getQueryParams(params))
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		a.logger.Error("Error in creating request to AI agent", zap.Error(err))
		params.ErrChan <- err
		close(params.ErrChan)
		close(params.DataChan)
		return
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := a.httpClient.Do(req)
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

	a.handleChatStream(ctx, resp.Body, params.DataChan, params.ErrChan)
	return
}

// getQueryParams extracts query parameters from ChatParams
func getQueryParams(params *models.AIAgentChatParams) map[string][]string {
	queryParams := make(map[string][]string)

	if len(params.ProjectIDs) != 0 {
		queryParams["project_id"] = params.ProjectIDs
	}

	if len(params.DatasetIDs) != 0 {
		queryParams["dataset_id"] = params.DatasetIDs
	}

	if params.UserInput != "" {
		queryParams["user_input"] = []string{params.UserInput}
	}

	return queryParams
}

// handleChatStream processes the streaming response from the AI agent
func (a *aiAgent) handleChatStream(ctx context.Context, body io.ReadCloser, dataChan chan<- []byte, errChan chan<- error) {
	defer close(dataChan)
	defer close(errChan)

	scanner := bufio.NewScanner(body)
	// Set a reasonable buffer size based on expected message size
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	lastMessageTime := time.Now()

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			// Handle context cancellation
			errChan <- ctx.Err()
			return
		default:
			now := time.Now()
			timeSinceLastMessage := now.Sub(lastMessageTime)
			lastMessageTime = now

			line := bytes.TrimSpace(scanner.Bytes())
			line = bytes.TrimPrefix(line, []byte("data:"))

			// ignore empty lines
			if len(line) == 0 {
				continue
			}

			var partialResponse SSEEvent
			if err := json.Unmarshal(line, &partialResponse); err != nil {
				a.logger.Error("Error in unmarshalling SSE event", zap.Error(err))
				errChan <- err
				return
			}

			if partialResponse.EventData.Error != nil {
				// Safe type assertion with check
				if errorStr, ok := partialResponse.EventData.Error.(string); ok {
					a.logger.Error("Error in SSE event", zap.String("error", errorStr))
					errChan <- fmt.Errorf("error in SSE event: %s", errorStr)
				} else {
					a.logger.Error("Error in SSE event", zap.Any("error", partialResponse.EventData.Error))
					errChan <- fmt.Errorf("error in SSE event: %v", partialResponse.EventData.Error)
				}
				return
			}

			a.logger.Info("Received SSE event",
				zap.String("event_node", partialResponse.EventNode),
				zap.String("status", partialResponse.Status),
				zap.String("message", partialResponse.Message),
				zap.Duration("time_since_last_message", timeSinceLastMessage))

			if partialResponse.EventData.Result != nil {
				result, err := json.Marshal(partialResponse.EventData.Result)
				if err != nil {
					a.logger.Error("Error in marshalling SSE event data", zap.Error(err))
					errChan <- err
					return
				}
				dataChan <- result
			}
		}
	}

	if err := scanner.Err(); err != nil {
		a.logger.Error("Error in scanning SSE event", zap.Error(err))
		errChan <- err
		return
	}

	// Only send EOF if no other errors occurred
	errChan <- io.EOF
}
