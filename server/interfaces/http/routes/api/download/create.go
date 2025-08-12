package download

import (
	"bufio"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Create and stream a download
// @Description Create a new download request and stream the progress via Server-Sent Events (SSE)
// @Tags downloads
// @Accept json
// @Produce text/event-stream
// @Param download body models.CreateDownloadRequest true "Download request object"
// @Success 200 {string} string "SSE stream of download progress"
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 500 {object} responses.ErrorResponse "Could not initiate download stream"
// @Router /v1/api/downloads [post]
// @Security Bearer
func (h *httpHandler) createAndStream(c *fiber.Ctx) error {
	userID := c.Locals(middleware.UserCtxKey).(string)
	orgID := c.Locals(middleware.OrganizationCtxKey).(string)

	var req models.CreateDownloadRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}
	req.UserID = userID
	req.OrgID = orgID

	// This part remains the same. It initiates the request to the downstream service.
	dataChan, err := h.service.CreateAndStream(&req)
	if err != nil {
		h.logger.Error("Failed to start download stream", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not initiate download stream"})
	}

	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("Transfer-Encoding", "chunked")

	c.Response().SetBodyStreamWriter(func(w *bufio.Writer) {
		for sse := range dataChan {
			if sse.Error != nil {
				h.logger.Error("Error received from stream source", zap.Error(sse.Error))
				return
			}

			if _, err := w.Write(sse.Data); err != nil {
				h.logger.Error("Error writing to client stream", zap.Error(err))
				return
			}

			if err := w.Flush(); err != nil {
				h.logger.Error("Error flushing client stream", zap.Error(err))
				return
			}
		}
	})

	return nil
}
