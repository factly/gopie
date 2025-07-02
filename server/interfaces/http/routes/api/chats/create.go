package chats

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	// Assuming these are your correct project paths

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
)

// @Description Request body for creating a streaming chat conversation with an AI agent - OpenAI compatible
type chatWithAgentRequestBody struct {
	Model       string                 `json:"model"`
	Messages    []models.AIChatMessage `json:"messages" validate:"required,dive"`
	Stream      bool                   `json:"stream" validate:"omitempty" default:"true"`
	Temperature float64                `json:"temperature" validate:"omitempty"`
	MaxTokens   int                    `json:"max_tokens" validate:"omitempty"`
}

// @Summary Chat with AI agent
// @Description Create a streaming chat conversation with an AI agent about datasets or projects
// @Tags chat
// @Accept json
// @Produce text/event-stream
// @Param body body chatWithAgentRequestBody true "Chat request parameters"
// @Param x-user-id header string true "User ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param x-project-ids header string false "Comma-separated project IDs" example:"550e8400-e29b-41d4-a716-446655440000,660e8400-e29b-41d4-a716-446655440001"
// @Param x-dataset-ids header string false "Comma-separated dataset IDs" example:"550e8400-e29b-41d4-a716-446655440000,660e8400-e29b-41d4-a716-446655440001"
// @Param x-chat-id header string false "Chat ID for continuing existing conversation" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {string} string "Server-sent events stream started"
// @Failure 400 {string} string "Invalid request body"
// @Failure 401 {string} string "Unauthorized - User ID is required"
// @Failure 500 {string} string "Internal server error"
// @Router /v1/api/chat/completions [post]
func (h *httpHandler) chatWithAgent(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

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

	// Retrieve identifiers from headers
	projectIDs := ctx.Get("x-project-ids")
	datasetIDs := ctx.Get("x-dataset-ids")

	for _, id := range strings.Split(datasetIDs, ",") {
		if strings.HasPrefix(id, "gp_") {
			dataset, err := h.datasetSvc.GetByTableName(id, orgID)
			if err != nil {
				h.logger.Error("Error fetching dataset by table name", zap.Error(err), zap.String("table_name", id))
				return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error":   "Failed to fetch dataset",
					"message": err.Error(),
					"code":    fiber.StatusInternalServerError,
				})
			}

			// now replace the dataset ID with the actual ID
			datasetIDs = strings.Replace(datasetIDs, id, dataset.ID, 1)
		}
	}

	if projectIDs == "" && datasetIDs == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Missing identifiers",
			"message": "At least one x-project-ids or x-dataset-ids header is required",
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

	chatIdHeader := ctx.Get("x-chat-id")
	sessionID := chatIdHeader

	prevMessages := []*models.ChatMessage{}
	var err error
	if sessionID != "" {
		// Fetch previous messages if chat ID is provided
		prevMessages, err = h.chatSvc.GetChatMessages(sessionID)
		if err != nil {
			h.logger.Error("Error fetching previous chat messages", zap.Error(err), zap.String("session_id", sessionID))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "Failed to fetch previous chat messages",
				"message": err.Error(),
				"code":    fiber.StatusInternalServerError,
			})
		}
	} else {
		sessionUUID, err := uuid.NewV6()
		if err != nil {
			h.logger.Error("Error generating new session ID", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "Failed to generate session ID",
				"message": err.Error(),
				"code":    fiber.StatusInternalServerError,
			})
		}
		sessionID = sessionUUID.String()
	}

	aiPrevMessages := make([]models.AIChatMessage, 0, len(prevMessages))
	for _, msg := range prevMessages {
		if msg.Choices != nil && len(msg.Choices) > 0 {
			if msg.Choices[0].Delta.Role != nil && msg.Choices[0].Delta.Content != nil {
				aiPrevMessages = append(aiPrevMessages, models.AIChatMessage{
					Role:    *msg.Choices[0].Delta.Role,
					Content: *msg.Choices[0].Delta.Content,
				})
			}
		}
	}

	params := &models.AIAgentChatParams{
		ProjectIDs:   projectIDs,
		DatasetIDs:   datasetIDs,
		Messages:     body.Messages,
		PrevMessages: aiPrevMessages,
		DataChan:     dataChan,
		ErrChan:      errChan,
	}

	ctx.Context().SetBodyStreamWriter(fasthttp.StreamWriter(func(w *bufio.Writer) {
		defer func() {
			h.logger.Info("SSE: Stream writer finished.", zap.String("session_id", sessionID))
		}()

		go h.chatSvc.ChatWithAiAgent(context.Background(), params)

		h.logger.Debug("SSE: Connection established, starting stream.", zap.String("session_id", sessionID))

		assistantMessageBuilder := strings.Builder{}
		assistantMessage := models.ChatMessage{}
		role := "user"
		messages := []models.ChatMessage{
			{
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
				data.ID = sessionID

				if data.Choices != nil && len(data.Choices) > 0 &&
					data.Choices[0].Delta.Role != nil &&
					*data.Choices[0].Delta.Role == "assistant" {
					if data.Choices[0].Delta.Content != nil {
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
					}
				} else {
					messages = append(messages, data)
				}

				dataToSend, _ = json.Marshal(data)

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
					if chatIdHeader == "" {
						chatWithMessages, err = h.chatSvc.CreateChat(context.Background(), &models.CreateChatParams{
							ID:             sessionID,
							Messages:       messages,
							CreatedBy:      userID,
							OrganizationID: orgID,
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
						_, err := h.chatSvc.AddNewMessage(context.Background(), chatIdHeader, messages)
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
