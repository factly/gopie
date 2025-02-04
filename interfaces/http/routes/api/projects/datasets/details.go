package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) details(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	dataset, err := h.svc.Details(datasetID)
	if err != nil {
		h.logger.Error("Error fetching dataset details", zap.Error(err), zap.String("datasetID", datasetID))
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Dataset not found",
				"message": "The requested dataset does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(dataset)
}
