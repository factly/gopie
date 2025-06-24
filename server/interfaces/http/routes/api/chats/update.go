package chats

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type UpdateChatVisibilityParams struct {
	Visibility string `json:"visibility" validate:"required,oneof=public private organization"`
}

func (h *httpHandler) updateVisibility(c *fiber.Ctx) error {
	var params UpdateChatVisibilityParams
	if err := c.BodyParser(&params); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	chatID := c.Params("chat_id")
	userID := c.Locals(middleware.UserCtxKey).(string)

	svcParams := &models.UpdateChatVisibilityParams{
		Visibility: params.Visibility,
	}

	chat, err := h.chatSvc.UpdateChatVisibility(chatID, userID, svcParams)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to update chat visibility")
	}

	return c.JSON(map[string]interface{}{
		"data": chat,
	})
}
