package download

import (
	"strconv"

	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) list(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)

	limit, _ := strconv.Atoi(c.Query("limit", "10"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	downloads, err := h.service.List(userID, orgID, limit, offset)
	if err != nil {
		h.logger.Error("Failed to list downloads", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not retrieve downloads"})
	}

	return c.JSON(downloads)
}
