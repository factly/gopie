package chats

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
)

// @Summary Delete chat
// @Description Delete an entire chat and all its messages
// @Tags chat
// @Accept json
// @Produce json
// @Param chatID path string true "Chat ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param x-user-id header string true "User ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 204 "Chat deleted successfully"
// @Failure 404 {object} responses.ErrorResponse "Chat not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/chat/{chatID} [delete]
func (h *httpHandler) deleteChat(ctx *fiber.Ctx) error {
	chatID := ctx.Params("chatID")
	userID := ctx.Get("x-user-id")

	err := h.chatSvc.DeleteChat(chatID, userID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Chat not found",
				"message": "The requested chat does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting chat",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.SendStatus(fiber.StatusNoContent)
}

// // @Summary Delete chat message
// // @Description Delete a specific message from a chat
// // @Tags chats
// // @Accept json
// // @Produce json
// // @Param chatID path string true "Chat ID" example:"550e8400-e29b-41d4-a716-446655440000"
// // @Param messageID path string true "Message ID" example:"550e8400-e29b-41d4-a716-446655440000"
// // @Success 204 "Message deleted successfully"
// // @Failure 404 {object} responses.ErrorResponse "Message not found"
// // @Failure 500 {object} responses.ErrorResponse "Internal server error"
// // @Router /v1/api/chats/{chatID}/messages/{messageID} [delete]
// func (h *httpHandler) deleteMessage(ctx *fiber.Ctx) error {
// 	chatID := ctx.Params("chatID")
// 	messageID := ctx.Params("messageID")
//
// 	err := h.chatSvc.DeleteMessage(chatID, messageID)
// 	if err != nil {
// 		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
// 			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
// 				"error":   "Message not found",
// 				"message": "The requested message does not exist",
// 				"code":    fiber.StatusNotFound,
// 			})
// 		}
// 		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
// 			"error":   err.Error(),
// 			"message": "Error deleting message",
// 			"code":    fiber.StatusInternalServerError,
// 		})
// 	}
//
// 	return ctx.SendStatus(fiber.StatusNoContent)
// }
