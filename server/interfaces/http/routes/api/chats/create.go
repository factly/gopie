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

	for id := range strings.SplitSeq(datasetIDs, ",") {
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
		if len(msg.Choices) > 0 {
			if msg.Choices[0].Delta.Role != nil && msg.Choices[0].Delta.Content != nil {
				aiPrevMessages = append(aiPrevMessages, models.AIChatMessage{
					Role:      *msg.Choices[0].Delta.Role,
					Content:   *msg.Choices[0].Delta.Content,
					ToolCalls: msg.Choices[0].Delta.ToolCalls,
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
		userToolCalls := []any{}
		assistantToolCalls := []any{}
		role := "user"
		assistantRole := "assistant"

		// This logic remains the same
		type contextArgs struct {
			ProjectIDs []string `json:"project_ids,omitempty"`
			DatasetIDs []string `json:"dataset_ids,omitempty"`
		}
		args := contextArgs{}
		if projectIDs != "" {
			args.ProjectIDs = strings.Split(projectIDs, ",")
		}
		if datasetIDs != "" {
			args.DatasetIDs = strings.Split(datasetIDs, ",")
		}
		if len(args.ProjectIDs) > 0 || len(args.DatasetIDs) > 0 {
			argsJSON, err := json.Marshal(args)
			if err != nil {
				h.logger.Error("Failed to marshal context tool call arguments", zap.Error(err), zap.String("session_id", sessionID))
			} else {
				type functionCall struct {
					Name      string `json:"name"`
					Arguments string `json:"arguments"`
				}
				type toolCall struct {
					Type     string       `json:"type"`
					Function functionCall `json:"function"`
				}
				contextToolCall := toolCall{
					Type: "function",
					Function: functionCall{
						Name:      "set_context",
						Arguments: string(argsJSON),
					},
				}
				userToolCalls = append(userToolCalls, contextToolCall)
			}
		}
		messages := []models.ChatMessage{
			{
				CreatedAt: time.Now(),
				Model:     "gopie-chat",
				Object:    "user.message",
				Choices: []models.Choice{
					{
						Delta: models.Delta{
							Role:      &role,
							Content:   &body.Messages[len(body.Messages)-1].Content,
							ToolCalls: userToolCalls,
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
				h.logger.Debug("SSE: Data chuck received", zap.Int("bytes", len(dataToSend)))

				// accumulate assistant messages
				var data models.ChatMessage
				_ = json.Unmarshal(dataChunk, &data)
				data.ID = sessionID

				if len(data.Choices) > 0 {
					choice := data.Choices[0]

					if choice.Delta.Content != nil {
						assistantMessageBuilder.WriteString(*choice.Delta.Content)
					}

					if len(choice.Delta.ToolCalls) > 0 {
						assistantToolCalls = append(assistantToolCalls, choice.Delta.ToolCalls...)
					}

					s := assistantMessageBuilder.String()
					assistantMessage = models.ChatMessage{
						ID:        data.ID,
						CreatedAt: data.CreatedAt,
						Model:     data.Model,
						Object:    data.Object,
						Choices: []models.Choice{
							{
								Delta: models.Delta{
									Role:         &assistantRole,
									FunctionCall: choice.Delta.FunctionCall,
									Refusal:      choice.Delta.Refusal,
									ToolCalls:    assistantToolCalls,
									Content:      &s,
								},
							},
						},
					}
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
					doneEvent := map[string]any{
						"id":      sessionID,
						"object":  "chat.completion.chunk",
						"created": time.Now().Unix(),
						"model":   "gopie-chat",
						"choices": []map[string]any{
							{
								"index":         0,
								"delta":         map[string]any{},
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
				errorPayload := map[string]any{
					"error": map[string]any{
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
