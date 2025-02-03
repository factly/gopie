package datasets

import (
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) delete(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	err := h.svc.Delete(datasetID)
	if err != nil {
		h.logger.Error("Error deleting dataset", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.SendStatus(fiber.StatusNoContent)
}
