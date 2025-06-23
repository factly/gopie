package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get dataset details
// @Description Get details of a specific dataset in a project
// @Tags datasets
// @Accept json
// @Produce json
// @Param projectID path string true "Project ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param datasetID path string true "Dataset ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} models.Dataset
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID}/datasets/{datasetID} [get]
func (h *httpHandler) details(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	dataset, err := h.datasetsSvc.Details(datasetID, orgID)
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
