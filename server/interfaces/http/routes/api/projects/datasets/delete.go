package datasets

import (
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Delete dataset
// @Description Delete a dataset from a project
// @Tags datasets
// @Accept json
// @Produce json
// @Param projectID path string true "Project ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param datasetID path string true "Dataset ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 204 "No Content"
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID}/datasets/{datasetID} [delete]
func (h *httpHandler) delete(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	dataset, err := h.datasetsSvc.Details(datasetID)
	if err != nil {
		h.logger.Error("Error deleting dataset", zap.Error(err), zap.String("datasetID", datasetID))
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
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

	err = h.datasetsSvc.Delete(datasetID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.olapSvc.DropTable(dataset.Name)
	if err != nil {
		h.logger.Error("Error dropping OLAP table", zap.Error(err), zap.String("datasetName", dataset.Name))
		err = retryDropTable(h, dataset.Name)
		if err != nil {
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error dropping OLAP table",
				"code":    fiber.StatusInternalServerError,
			})
		}
	}

	return ctx.SendStatus(fiber.StatusNoContent)
}

func retryDropTable(h *httpHandler, datasetName string) error {
	for i := 0; i < 3; i++ {
		err := h.olapSvc.DropTable(datasetName)
		if err == nil {
			return nil
		}
		h.logger.Warn("Retrying to drop OLAP table", zap.Error(err), zap.String("datasetName", datasetName))
	}

	return errors.New("failed to drop OLAP table after retries")
}
