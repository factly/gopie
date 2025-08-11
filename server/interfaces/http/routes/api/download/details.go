package download

import (
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) get(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)
	downloadID := c.Params("id")

	if downloadID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "download ID is required"})
	}

	download, err := h.service.Get(downloadID, userID, orgID)
	if err != nil {
		h.logger.Error("Failed to get download", zap.String("id", downloadID), zap.Error(err))
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "download not found"})
	}

	return c.JSON(download)
}
