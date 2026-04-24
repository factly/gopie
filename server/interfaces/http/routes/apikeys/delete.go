package apikeys

import (
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) delete(ctx *fiber.Ctx) error {
	id := ctx.Params("id")
	if id == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "ID is required",
			"message": "API key ID is required in path",
		})
	}

	if err := h.apikeyService.DeleteAPIKey(ctx.Context(), id); err != nil {
		h.logger.Error("Error deleting API key", zap.Error(err), zap.String("id", id))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting API key",
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"message": "API key deleted successfully",
	})
}
