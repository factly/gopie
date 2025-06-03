package chats

import (
	"strconv"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

// @Summary Get chat messages
// @Description Get all messages from a specific chat with pagination
// @Tags chat
// @Accept json
// @Produce json
// @Param chatID path string true "Chat ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param limit query integer false "Number of messages per page" default(10)
// @Param page query integer false "Page number" default(1)
// @Success 200 {object} responses.SuccessResponse{data=[]models.ChatMessage} "Chat messages retrieved successfully"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/chat/{chatID}/messages [get]
func (s *httpHandler) getChatMessages(ctx *fiber.Ctx) error {
	chatID := ctx.Params("chatID")
	limit := ctx.Query("limit")
	page := ctx.Query("page")
	pagination := models.NewPagination()
	l, err := strconv.Atoi(limit)
	if err != nil {
		l = 10
	}
	p, err := strconv.Atoi(page)
	if err != nil {
		p = 1
	}

	pagination.Limit = l
	pagination.Offset = (p - 1) * l
	messages, err := s.chatSvc.GetChatMessages(chatID, pagination)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching chat messages",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": messages,
	})
}

// @Summary List dataset chats
// @Description Get all chats associated with a specific dataset with pagination
// @Tags chat
// @Accept json
// @Produce json
// @Param dataset_id query string true "Dataset ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param limit query integer false "Number of chats per page" default(10)
// @Param page query integer false "Page number" default(1)
// @Success 200 {object} responses.SuccessResponse{data=[]models.Chat} "Dataset chats retrieved successfully"
// @Failure 400 {object} responses.ErrorResponse "Dataset ID is required"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/chat [get]
func (h *httpHandler) listDatasetChats(ctx *fiber.Ctx) error {
	datasetID := ctx.Query("dataset_id")
	if datasetID == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "dataset_id is required",
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}
	limit := ctx.Query("limit")
	page := ctx.Query("page")
	pagination := models.NewPagination()
	l, err := strconv.Atoi(limit)
	if err != nil {
		l = 10
	}
	p, err := strconv.Atoi(page)
	if err != nil {
		p = 1
	}

	pagination.Limit = l
	pagination.Offset = (p - 1) * l

	chats, err := h.chatSvc.GetChatsByDatasetID(datasetID, pagination)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching chats",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": chats,
	})
}
