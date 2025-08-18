package download

import (
	"strconv"

	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary List downloads
// @Description Get a paginated list of downloads for the authenticated user
// @Tags downloads
// @Accept json
// @Produce json
// @Param limit query int false "Number of items to return" default(10)
// @Param offset query int false "Number of items to skip" default(0)
// @Success 200 {array} models.Download "List of downloads"
// @Failure 500 {object} responses.ErrorResponse "Could not retrieve downloads"
// @Router /v1/api/downloads [get]
// @Security Bearer
func (h *httpHandler) list(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)

	limit, _ := strconv.Atoi(c.Query("limit", "10"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	downloads, err := h.service.List(userID, orgID, int32(limit), int32(offset))
	if err != nil {
		h.logger.Error("Failed to list downloads", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not retrieve downloads"})
	}

	return c.JSON(downloads)
}
