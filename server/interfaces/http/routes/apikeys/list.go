package apikeys

import (
	"strconv"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) list(ctx *fiber.Ctx) error {
	pageStr := ctx.Query("page", "1")
	limitStr := ctx.Query("limit", strconv.Itoa(models.DefaultLimit))

	page, err := strconv.Atoi(pageStr)
	if err != nil || page < 1 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid page parameter",
			"message": "Page must be a positive integer",
		})
	}

	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit < 1 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid limit parameter",
			"message": "Limit must be a positive integer",
		})
	}

	result, err := h.apikeyService.SearchAPIKeys(ctx.Context(), "", models.Pagination{
		Limit:  limit,
		Offset: (page - 1) * limit,
	})
	if err != nil {
		h.logger.Error("Error listing API keys", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error listing API keys",
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(result)
}
