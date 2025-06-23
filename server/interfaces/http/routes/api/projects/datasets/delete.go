package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/interfaces/http/middleware"
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

	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	dataset, err := h.datasetsSvc.Details(datasetID, orgID)
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

	err = h.datasetsSvc.Delete(datasetID, orgID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.olapSvc.DropTable(dataset.Name)

	return ctx.SendStatus(fiber.StatusNoContent)
}
