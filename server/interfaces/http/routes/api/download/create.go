package download

import (
	"io"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) createAndStream(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)

	var req models.CreateDownloadRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}
	req.UserID = userID
	req.OrgID = orgID

	streamBody, err := h.service.CreateAndStream(&req)
	if err != nil {
		h.logger.Error("Failed to start download stream", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not initiate download stream"})
	}
	defer streamBody.Close()

	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")

	if _, err := io.Copy(c.Response().BodyWriter(), streamBody); err != nil {
		h.logger.Error("Error while streaming SSE events", zap.Error(err))
	}

	return nil
}
