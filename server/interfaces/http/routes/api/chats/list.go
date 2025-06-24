package chats

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
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

	messages, err := s.chatSvc.GetChatMessages(chatID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching chat messages",
			"code":    fiber.StatusInternalServerError,
		})
	}
	for _, msg := range messages {
		msg.ChatID = chatID
	}

	return ctx.JSON(map[string]interface{}{
		"data": messages,
	})
}

// @Summary List user chats
// @Description Get all chats for a specific user with pagination
// @Tags chat
// @Accept json
// @Produce json
// @Param x-user-id header string true "User ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param limit query integer false "Number of chats per page" default(10)
// @Param page query integer false "Page number" default(1)
// @Success 200 {object} map[string]interface{} "User chats retrieved successfully"
// @Failure 401 {object} map[string]interface{} "Unauthorized - User ID is required"
// @Failure 500 {object} map[string]interface{} "Internal server error"
// @Router /v1/api/chat [get]
func (s *httpHandler) listUserChats(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	pagination := models.NewPagination()
	limit, page := pkg.ParseLimitAndPage(ctx.Query("limit"), ctx.Query("page"))

	pagination.Limit = limit
	pagination.Offset = (page - 1) * limit

	chats, err := s.chatSvc.ListUserChats(userID, orgID, pagination)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching user chats",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": chats,
	})
}
