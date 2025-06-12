package chats

import "github.com/gofiber/fiber/v2"

// GetChatDetails godoc
// @Summary Get chat details
// @Description Retrieve detailed information about a specific chat by its ID
// @Tags chats
// @Accept json
// @Produce json
// @Param chatID path string true "Chat ID"
// @Param userID header string true "User ID"
// @Success 200 {object} map[string]interface{} "Chat details retrieved successfully"
// @Failure 400 {object} map[string]interface{} "Bad request - Chat ID is required"
// @Failure 401 {object} map[string]interface{} "Unauthorized - User ID is required"
// @Failure 500 {object} map[string]interface{} "Internal server error"
// @Router /api/chats/{chatID} [get]
func (h *httpHandler) details(ctx *fiber.Ctx) error {
	chatID := ctx.Params("chatID")
	if chatID == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Chat ID is required",
			"message": "Chat ID cannot be empty",
			"code":    fiber.StatusBadRequest,
		})
	}

	userID := ctx.Get("userID")
	if userID == "" {
		return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error":   "Unauthorized",
			"message": "User ID is required",
			"code":    fiber.StatusUnauthorized,
		})
	}

	chat, err := h.chatSvc.GetChatByID(chatID, userID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching chat details",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": chat,
	})
}
