package datasets

import (
	"errors"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (h *httpHandler) delete(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	err := h.svc.Delete(datasetID)
	if err != nil {
		h.logger.Error("Error deleting dataset", zap.Error(err), zap.String("datasetID", datasetID))
		if errors.Is(err, pgx.ErrNoRows) {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Dataset not found",
				"message": "The requested dataset does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.SendStatus(fiber.StatusNoContent)
}
