package chats

import (
	"strconv"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

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
