package download

import (
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get download details
// @Description Get details of a specific download by ID
// @Tags downloads
// @Accept json
// @Produce json
// @Param id path string true "Download ID"
// @Success 200 {object} models.Download "Download details"
// @Failure 400 {object} responses.ErrorResponse "Download ID is required"
// @Failure 404 {object} responses.ErrorResponse "Download not found"
// @Router /v1/api/downloads/{id} [get]
// @Security Bearer
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
