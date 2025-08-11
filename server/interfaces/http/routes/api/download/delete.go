package download

import (
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) delete(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)
	downloadID := c.Params("id")

	if downloadID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "download ID is required"})
	}

	err := h.service.Delete(downloadID, userID, orgID)
	if err != nil {
		h.logger.Error("Failed to delete download", zap.String("id", downloadID), zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not delete download"})
	}

	return c.SendStatus(fiber.StatusNoContent)
}
