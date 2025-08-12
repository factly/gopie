package download

import (
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Delete a download
// @Description Delete a specific download by ID
// @Tags downloads
// @Accept json
// @Produce json
// @Param id path string true "Download ID"
// @Success 204 "Download deleted successfully"
// @Failure 400 {object} responses.ErrorResponse "Download ID is required"
// @Failure 500 {object} responses.ErrorResponse "Could not delete download"
// @Router /v1/api/downloads/{id} [delete]
// @Security Bearer
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
