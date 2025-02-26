package chats

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
)

func (h *httpHandler) deleteChat(ctx *fiber.Ctx) error {
	chatID := ctx.Params("chatID")

	err := h.chatSvc.DeleteChat(chatID)
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

func (h *httpHandler) deleteMessage(ctx *fiber.Ctx) error {
	chatID := ctx.Params("chatID")
	messageID := ctx.Params("messageID")

	err := h.chatSvc.DeleteMessage(chatID, messageID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Message not found",
				"message": "The requested message does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting message",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.SendStatus(fiber.StatusNoContent)
}
