package chats

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type UpdateChatVisibilityParams struct {
	Visibility string `json:"visibility" validate:"required,oneof=public private organization"`
}

// UpdateChatVisibility godoc
// @Summary Update chat visibility
// @Description Update the visibility setting of a specific chat
// @Tags chat
// @Accept json
// @Produce json
// @Param chat_id path string true "Chat ID"
// @Param request body UpdateChatVisibilityParams true "Update chat visibility request"
// @Success 200 {object} map[string]interface{} "Successfully updated chat visibility"
// @Failure 400 {object} map[string]string "Invalid request body"
// @Failure 500 {object} map[string]string "Failed to update chat visibility"
// @Security BearerAuth
// @Router /api/chats/{chat_id}/visibility [put]
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
