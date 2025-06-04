package chats

import (
	"bufio"
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	// Assuming these are your correct project paths
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
)

// chatRequestBody represents the request body for chat interaction
// @Description Request body for creating or continuing a chat conversation
type chatRequestBody struct {
	// Unique identifier of an existing chat (optional for new chats)
	ChatID string `json:"chat_id" validate:"omitempty,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// ID of the dataset to analyze
	DatasetID string `json:"dataset_id" validate:"omitempty,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// User ID of the creator
	CreatedBy string `json:"created_by" validate:"omitempty" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Array of chat messages
	Messages []struct {
		// Message content
		Content string `json:"content" validate:"required" example:"Show me the total sales by region"`
		// Message role (user/assistant)
		Role string `json:"role" validate:"required" example:"user"`
	} `json:"messages" validate:"required"`
}

// @Summary Create or continue chat
// @Description Create a new chat or continue an existing chat conversation with AI about a dataset
// @Tags chats
// @Accept json
// @Produce json
// @Param body body chatRequestBody true "Chat request parameters"
// @Success 201 {object} models.ChatWithMessages "Chat created/continued successfully" // Ensure models.ChatWithMessages is the correct response structure
// @Failure 400 {object} map[string]interface{} "Invalid request body"
// @Failure 404 {object} map[string]interface{} "Dataset not found"
// @Failure 500 {object} map[string]interface{} "Internal server error"
// @Router /v1/api/chats [post]
func (h *httpHandler) chat(ctx *fiber.Ctx) error {
	body := chatRequestBody{}
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body (validation failed)",
			"code":    fiber.StatusBadRequest,
		})
	}

	if len(body.Messages) == 0 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "messages field is required and cannot be empty",
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}
	body.Messages[len(body.Messages)-1].Role = "user"

	dataset, err := h.datasetSvc.Details(body.DatasetID)
	if err != nil {
		if domain.IsStoreError(err) && errors.Is(err, domain.ErrRecordNotFound) {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Dataset not found",
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching dataset details", zap.Error(err), zap.String("dataset_id", body.DatasetID))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to fetch dataset details",
			"message": err.Error(), // Provide error message for better debugging on client side if appropriate
			"code":    fiber.StatusInternalServerError,
		})
	}

	schemaRes, err := h.olapSvc.GetTableSchema(dataset.Name)
	if err != nil {
		h.logger.Error("Error getting table schema", zap.Error(err), zap.String("table_name", dataset.Name))
		if strings.Contains(err.Error(), "does not exist") { // Simpler check
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   domain.ErrTableNotFound.Error(),
				"message": fmt.Sprintf("Table '%s' not found in OLAP source", dataset.Name),
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to get table schema",
			"message": err.Error(),
			"code":    fiber.StatusInternalServerError,
		})
	}

	randomNRows, err := h.olapSvc.ExecuteQuery(fmt.Sprintf("select * from %s order by random() limit 50", dataset.Name))
	if err != nil {
		h.logger.Error("Error fetching sample data", zap.Error(err), zap.String("table_name", dataset.Name))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to fetch sample data",
			"message": err.Error(),
			"code":    fiber.StatusInternalServerError,
		})
	}

	schemaJson := convertSchemaToJson(h.logger, schemaRes)
	rowsCsv := convertRowsToCSV(h.logger, randomNRows)

	prompt := fmt.Sprintf(`
You are a DuckDB and data expert. Review the user's question and respond appropriately:

1. For SQL queries, format your response as:
---SQL---
<SQL query here without semicolon>
---SQL---

2. For non-SQL responses (like general questions), format as:
---TEXT---
<Your response here>
---TEXT---

USER QUESTION: %s 

TABLE NAME: %s

TABLE SCHEMA IN JSON: 
---------------------
%s
---------------------

RANDOM 50 ROWS IN CSV: 
---------------------
%s
---------------------

RULES FOR SQL QUERIES:
- No semicolon at end of query
- Use double quotes for table/column names, single quotes for values
- Exclude rows with state='All India' when filtering/aggregating by state 
- For share/percentage calculations, calculate as: (value/total)*100
- Exclude 'Total' category from categorical field calculations
- Include units/unit column when displaying value columns
- Use Levenshtein for fuzzy string matching
- Use ILIKE for case-insensitive matching
- Generate only read queries (SELECT)
        `, body.Messages[len(body.Messages)-1].Content, dataset.Name, schemaJson, rowsCsv)

	messages := make([]models.D_ChatMessage, 0, len(body.Messages))
	for _, m := range body.Messages {
		messages = append(messages, models.D_ChatMessage{
			Content: m.Content,
			Role:    m.Role,
		})
	}

	chatWithMessages, err := h.chatSvc.D_ChatWithAi(&models.D_ChatWithAiParams{
		ChatID:    body.ChatID,
		DatasetID: body.DatasetID,
		CreatedBy: body.CreatedBy,
		Messages:  messages,
		Prompt:    prompt,
	})
	if err != nil {
		h.logger.Error("Error chatting with AI", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to chat with AI",
			"message": err.Error(),
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": chatWithMessages,
	})
}

func convertSchemaToJson(logger *logger.Logger, schema any) string {
	schemaJsonBytes, err := json.Marshal(schema)
	if err != nil {
		logger.Error("Failed to marshal schema to JSON", zap.Error(err))
		return "{}" // Return empty JSON object on error
	}
	return string(schemaJsonBytes)
}

func convertRowsToCSV(logger *logger.Logger, rows []map[string]any) string {
	if len(rows) == 0 {
		return "" // No data, no CSV
	}

	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)

	headers := make([]string, 0, len(rows[0]))
	headerMap := make(map[string]bool) // To keep track of added headers
	for key := range rows[0] {
		headers = append(headers, key)
		headerMap[key] = true
	}
	for i := 1; i < len(rows); i++ {
		for key := range rows[i] {
			if !headerMap[key] {
				headers = append(headers, key)
				headerMap[key] = true
			}
		}
	}

	if err := writer.Write(headers); err != nil {
		logger.Error("Failed to write CSV headers", zap.Error(err))
		return "" // Error writing headers
	}

	for _, row := range rows {
		record := make([]string, len(headers))
		for i, header := range headers {
			if value, ok := row[header]; ok {
				record[i] = fmt.Sprintf("%v", value)
			} else {
				record[i] = ""
			}
		}
		if err := writer.Write(record); err != nil {
			logger.Error("Failed to write CSV record", zap.Error(err))
		}
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		logger.Error("CSV writer error after flush", zap.Error(err))
		return "" // Return empty string on final writer error
	}
	return buf.String()
}

// @Description Request body for creating a streaming chat conversation with an AI agent - OpenAI compatible
type chatWithAgentRequestBody struct {
	Model       string                 `json:"model"`
	Messages    []models.AIChatMessage `json:"messages" validate:"required,dive"`
	Stream      bool                   `json:"stream" validate:"omitempty" default:"true"`
	Temperature float64                `json:"temperature" validate:"omitempty"`
	MaxTokens   int                    `json:"max_tokens" validate:"omitempty"`
	Metadata    map[string]string      `json:"metadata" validate:"omitempty"`
	ChatID      string                 `json:"chat_id" validate:"omitempty,uuid"`
	CreatedBy   string                 `json:"created_by" validate:"required"`
}

// @Summary Chat with AI agent
// @Description Create a streaming chat conversation with an AI agent about datasets or projects
// @Tags chats
// @Accept json
// @Produce text/event-stream
// @Param body body chatWithAgentRequestBody true "Chat request parameters"
// @Success 200 {string} string "Server-sent events stream started"
// @Failure 400 {string} string "Invalid request body"
// @Failure 500 {string} string "Internal server error" // Should ideally be JSON for API consistency
// @Router /v1/api/chats/agent [post]
func (h *httpHandler) chatWithAgent(ctx *fiber.Ctx) error {
	var body chatWithAgentRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Error("Error parsing request body for agent chat", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid request body",
			"message": err.Error(),
			"code":    fiber.StatusBadRequest,
		})
	}

	if err := pkg.ValidateRequest(h.logger, &body); err != nil {
		h.logger.Error("Invalid request body for agent chat", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Validation failed",
			"message": err.Error(),
			"code":    fiber.StatusBadRequest,
		})
	}

	if body.Metadata["dataset_ids"] == "" && body.Metadata["project_ids"] == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Missing identifiers",
			"message": "At least one dataset_id or project_id is required",
			"code":    fiber.StatusBadRequest,
		})
	}
	if len(body.Messages) == 0 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Missing messages",
			"message": "messages field is required and cannot be empty",
			"code":    fiber.StatusBadRequest,
		})
	}

	ctx.Set("Content-Type", "text/event-stream")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")
	ctx.Set("Transfer-Encoding", "chunked")
	ctx.Set("X-Accel-Buffering", "no")

	dataChan := make(chan []byte, 10) // Buffered channel
	errChan := make(chan error, 1)    // Buffered channel for errors

	params := &models.AIAgentChatParams{
		ProjectIDs: body.Metadata["project_ids"],
		DatasetIDs: body.Metadata["dataset_ids"],
		Messages:   body.Messages,
		DataChan:   dataChan,
		ErrChan:    errChan,
	}

	sessionID := body.ChatID

	ctx.Context().SetBodyStreamWriter(fasthttp.StreamWriter(func(w *bufio.Writer) {
		defer func() {
			h.logger.Info("SSE: Stream writer finished.", zap.String("session_id", sessionID))
		}()

		go h.chatSvc.ChatWithAiAgent(context.Background(), params)

		h.logger.Debug("SSE: Connection established, starting stream.", zap.String("session_id", sessionID))

		initEvent := map[string]interface{}{
			"id":      sessionID,
			"object":  "chat.completion.chunk",
			"created": time.Now().Unix(),
			"model":   body.Model,
		}
		initData, marshalErr := json.Marshal(initEvent)
		if marshalErr != nil {
			h.logger.Error("SSE: Failed to marshal init event", zap.Error(marshalErr), zap.String("session_id", sessionID))
			fmt.Fprintf(w, "event: error\ndata: {\"error\":\"internal server error preparing stream\"}\n\n")
			w.Flush()
			return
		}
		if _, err := fmt.Fprintf(w, "data: %s\n\n", initData); err != nil {
			h.logger.Error("SSE: Error writing init event to stream", zap.Error(err), zap.String("session_id", sessionID))
			return
		}
		if err := w.Flush(); err != nil {
			h.logger.Error("SSE: Error flushing init event", zap.Error(err), zap.String("session_id", sessionID))
			return
		}

		assistantMessageBuilder := strings.Builder{}
		assistantMessage := models.ChatMessage{}
		role := "user"
		messages := []models.ChatMessage{
			{
				ID:        sessionID,
				CreatedAt: time.Now(),
				Model:     body.Model,
				Object:    "user.message",
				Choices: []models.Choice{
					{
						Delta: models.Delta{
							Role:    &role,
							Content: &body.Messages[len(body.Messages)-1].Content,
						},
					},
				},
			},
		}

		fmt.Println("Messages to send:", *messages[0].Choices[0].Delta.Role)

		for {
			select {
			case dataChunk, ok := <-dataChan:
				if !ok { // dataChan was closed by the service
					h.logger.Info("SSE: Data channel closed by service.", zap.String("session_id", sessionID))
					return
				}

				dataToSend := dataChunk

				// accumulate assistant messages
				var data models.ChatMessage
				_ = json.Unmarshal(dataChunk, &data)

				if data.Choices != nil && len(data.Choices) > 0 &&
					data.Choices[0].Delta.Role != nil &&
					*data.Choices[0].Delta.Role == "assistant" {
					fmt.Println("Received assistant message chunk:", *data.Choices[0].Delta.Content)
					assistantMessageBuilder.WriteString(*data.Choices[0].Delta.Content)
					s := assistantMessageBuilder.String()
					assistantMessage = models.ChatMessage{
						ID:        data.ID,
						CreatedAt: data.CreatedAt,
						Model:     data.Model,
						Object:    data.Object,
						Choices: []models.Choice{
							{
								Delta: models.Delta{
									Role:         data.Choices[0].Delta.Role,
									FunctionCall: data.Choices[0].Delta.FunctionCall,
									Refusal:      data.Choices[0].Delta.Refusal,
									ToolCalls:    data.Choices[0].Delta.ToolCalls,
									Content:      &s,
								},
							},
						},
					}
				} else {
					messages = append(messages, data)
				}
				var jsonObj interface{}

				trimmedChunk := bytes.TrimSpace(dataChunk)
				if len(trimmedChunk) > 0 && (trimmedChunk[0] == '{' || trimmedChunk[0] == '[') {
					if err := json.Unmarshal(trimmedChunk, &jsonObj); err == nil {
						compactData, marshalErr := json.Marshal(jsonObj)
						if marshalErr == nil {
							dataToSend = compactData
						} else {
							h.logger.Error("SSE: Failed to re-marshal JSON data", zap.Error(marshalErr), zap.String("session_id", sessionID))
						}
					} else {
						h.logger.Warn("SSE: Invalid JSON data received", zap.Error(err), zap.String("session_id", sessionID))
					}
				} else {
					h.logger.Debug("SSE: Non-JSON data chunk received", zap.String("session_id", sessionID))
				}

				if _, err := fmt.Fprintf(w, "data: %s\n\n", dataToSend); err != nil {
					h.logger.Error("SSE: Error writing data to stream", zap.Error(err), zap.String("session_id", sessionID))
					return
				}
				if err := w.Flush(); err != nil {
					h.logger.Error("SSE: Error flushing data to stream", zap.Error(err), zap.String("session_id", sessionID))
					return
				}

			case serviceErr, ok := <-errChan:
				if !ok {
					h.logger.Info("SSE: Error channel closed by service", zap.String("session_id", sessionID))
					return
				}

				if errors.Is(serviceErr, io.EOF) {

					// save the messages to database
					messages = append(messages, assistantMessage)

					var chatWithMessages *models.ChatWithMessages
					var err error
					if body.ChatID == "" {
						chatWithMessages, err = h.chatSvc.CreateChat(context.Background(), &models.CreateChatParams{
							Messages:  messages,
							CreatedBy: body.CreatedBy,
						})
						if err != nil {
							h.logger.Error("SSE: Error creating new chat", zap.Error(err), zap.String("session_id", sessionID))
							errorEvent := pkg.ChatMessageFromError(err)
							errorEvent.ID = sessionID // Ensure session ID is set for error event
							errorData, marshalErr := json.Marshal(errorEvent)
							if marshalErr != nil {
								h.logger.Error("SSE: Failed to marshal error event", zap.Error(marshalErr), zap.String("session_id", sessionID))
							}
							if _, err := fmt.Fprintf(w, "data: %s\n\n", errorData); err != nil {
								h.logger.Error("SSE: Error writing error event to stream", zap.Error(err), zap.String("session_id", sessionID))
							}
							return
						}
					} else {
						_, err := h.chatSvc.AddNewMessage(context.Background(), body.ChatID, messages)
						if err != nil {
							h.logger.Error("SSE: Error adding new message to existing chat", zap.Error(err), zap.String("session_id", sessionID))
							errorEvent := pkg.ChatMessageFromError(err)
							errorEvent.ID = sessionID // Ensure session ID is set for error event
							errorData, marshalErr := json.Marshal(errorEvent)
							if marshalErr != nil {
								h.logger.Error("SSE: Failed to marshal error event", zap.Error(marshalErr), zap.String("session_id", sessionID))
							}
							if _, err := fmt.Fprintf(w, "data: %s\n\n", errorData); err != nil {
								h.logger.Error("SSE: Error writing error event to stream", zap.Error(err), zap.String("session_id", sessionID))
							}
							return
						}
					}
					if sessionID == "" {
						sessionID = chatWithMessages.ID
					}

					h.logger.Info("SSE: Stream finished successfully (EOF received).", zap.String("session_id", sessionID))
					doneEvent := map[string]interface{}{
						"id":      sessionID,
						"object":  "chat.completion.chunk",
						"created": time.Now().Unix(),
						"model":   body.Model,
						"choices": []map[string]interface{}{
							{
								"index":         0,
								"delta":         map[string]interface{}{},
								"finish_reason": "stop",
							},
						},
					}
					doneData, marshalErr := json.Marshal(doneEvent)
					if marshalErr != nil {
						h.logger.Error("SSE: Failed to marshal final done event", zap.Error(marshalErr), zap.String("session_id", sessionID))
					} else {
						if _, err := fmt.Fprintf(w, "data: %s\n\n", doneData); err != nil {
							h.logger.Error("SSE: Error writing final done event to stream", zap.Error(err), zap.String("session_id", sessionID))
						}
					}
					if _, err := fmt.Fprintf(w, "data: [DONE]\n\n"); err != nil {
						h.logger.Error("SSE: Error writing [DONE] marker to stream", zap.Error(err), zap.String("session_id", sessionID))
					}
					if err := w.Flush(); err != nil {
						h.logger.Error("SSE: Error flushing [DONE] marker", zap.Error(err), zap.String("session_id", sessionID))
					}

					return
				}

				h.logger.Error("SSE: Error received from AI service.", zap.Error(serviceErr), zap.String("session_id", sessionID))
				errorPayload := map[string]interface{}{
					"error": map[string]interface{}{
						"message": serviceErr.Error(),
						"type":    "service_error",
					},
				}
				errorData, marshalErr := json.Marshal(errorPayload)
				if marshalErr != nil {
					h.logger.Error("SSE: Failed to marshal service error payload", zap.Error(marshalErr), zap.String("session_id", sessionID))
					fmt.Fprintf(w, "data: {\"error\": \"An unrecoverable error occurred in the service.\"}\n\n")
				} else {
					fmt.Fprintf(w, "data: %s\n\n", errorData)
				}
				fmt.Fprintf(w, "data: [DONE]\n\n")
				if err := w.Flush(); err != nil {
					h.logger.Error("SSE: Error flushing service error message and [DONE] marker", zap.Error(err), zap.String("session_id", sessionID))
				}
				return
			}
		}
	}))
	return nil
}
