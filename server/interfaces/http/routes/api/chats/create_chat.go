package chats

import (
	"time"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// @Description Request body for creating a new chat session
type createChatRequestBody struct {
	Title      string   `json:"title,omitempty"`
	DatasetIDs []string `json:"dataset_ids,omitempty"`
	ProjectIDs []string `json:"project_ids,omitempty"`
	MaxTokens  *int     `json:"maxTokens,omitempty" example:"1000"`
}

// @Description Response body for creating a new chat session
type createChatResponse struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
}

// @Summary Create a new chat session
// @Description Create a new chat session with a pre-generated ID before sending messages
// @Tags chat
// @Accept json
// @Produce json
// @Param body body createChatRequestBody false "Chat creation parameters"
// @Param x-user-id header string true "User ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 201 {object} createChatResponse "Chat created successfully"
// @Failure 400 {string} string "Invalid request body"
// @Failure 401 {string} string "Unauthorized - User ID is required"
// @Failure 500 {string} string "Internal server error"
// @Router /v1/api/chat/create [post]
func (h *httpHandler) createChat(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	var body createChatRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Error("Error parsing request body for chat creation", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid request body",
			"message": err.Error(),
			"code":    fiber.StatusBadRequest,
		})
	}

	// Generate a new UUID for the chat
	sessionUUID, err := uuid.NewV6()
	if err != nil {
		h.logger.Error("Error generating new session ID", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to generate session ID",
			"message": err.Error(),
			"code":    fiber.StatusInternalServerError,
		})
	}

	chatID := sessionUUID.String()

	// Set default title if not provided
	title := body.Title
	if title == "" {
		title = "New Chat " + time.Now().Format("Jan 2, 15:04")
	}

	// Create the chat parameters
	chatParams := &models.CreateChatParams{
		ID:             chatID,
		Title:          title,
		CreatedBy:      userID,
		Messages:       []models.ChatMessage{}, // Empty messages initially
		OrganizationID: orgID,
	}

	// Use the CreateChat service which now handles empty messages
	chatWithMessages, err := h.chatSvc.CreateChat(ctx.Context(), chatParams, body.MaxTokens)
	if err != nil {
		h.logger.Error("Error creating new chat", zap.Error(err), zap.String("chat_id", chatID))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Failed to create chat",
			"message": err.Error(),
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Chat created successfully",
		zap.String("chat_id", chatWithMessages.ID),
		zap.String("user_id", userID),
		zap.String("org_id", orgID))

	// Return the created chat details
	response := createChatResponse{
		ID:        chatWithMessages.ID,
		Title:     chatWithMessages.Title,
		CreatedAt: chatWithMessages.CreatedAt,
	}

	return ctx.Status(fiber.StatusCreated).JSON(response)
}