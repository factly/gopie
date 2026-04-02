package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get dataset column descriptions
// @Description Retrieve column descriptions and statistics for an existing dataset
// @ID get-dataset-column-descriptions
// @Tags datasets
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID"
// @Success 200 {object} responses.SuccessResponse{data=models.DatasetSummaryWithName}
// @Failure 404 {object} responses.ErrorResponse "Dataset not found or no summary exists"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/datasets/{datasetID}/column-descriptions [get]
func (h *httpHandler) getColumnDescriptions(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	// Get the dataset details to verify it exists and get the dataset name
	dataset, err := h.datasetsSvc.Details(datasetID, orgID)
	if err != nil {
		h.logger.Error("Error fetching dataset", zap.Error(err), zap.String("datasetID", datasetID))
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

	// Try to get the stored dataset summary from PostgreSQL (includes descriptions)
	storedSummary, err := h.datasetsSvc.GetDatasetSummary(dataset.Name)
	if err != nil {
		// If no stored summary exists, get fresh summary from OLAP
		h.logger.Info("No stored summary found, fetching from OLAP", zap.String("datasetID", datasetID))

		olapSummary, err := h.olapSvc.GetDatasetSummary(dataset.Name)
		if err != nil {
			h.logger.Error("Error fetching dataset summary from OLAP", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error fetching dataset summary",
				"code":    fiber.StatusInternalServerError,
			})
		}

		// Return OLAP summary (without descriptions)
		return ctx.JSON(map[string]*models.DatasetSummaryWithName{
			"data": {
				DatasetName: dataset.Name,
				Summary:     olapSummary,
			},
		})
	}

	// Return stored summary (includes descriptions if they were set)
	return ctx.JSON(map[string]*models.DatasetSummaryWithName{
		"data": storedSummary,
	})
}
