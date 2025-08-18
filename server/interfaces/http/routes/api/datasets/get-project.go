package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get project for dataset
// @Description Get the project ID for a specific dataset
// @Tags datasets
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} map[string]string
// @Failure 404 {object} responses.ErrorResponse "No project found for dataset"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/datasets/{datasetID}/project [get]
func (h *httpHandler) getProjectForDataset(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	
	projectID, err := h.datasetsSvc.GetProjectForDataset(datasetID)
	if err != nil {
		h.logger.Error("Error fetching project for dataset", zap.Error(err), zap.String("datasetID", datasetID))
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "No project found for dataset",
				"message": "The dataset is not associated with any project",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching project for dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	
	return ctx.JSON(fiber.Map{
		"project_id": projectID,
	})
}