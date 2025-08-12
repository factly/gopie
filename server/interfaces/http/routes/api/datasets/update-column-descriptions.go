package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type updateColumnDescriptionsParams struct {
	ColumnDescriptions map[string]string `json:"column_descriptions" validate:"required,min=1,dive,required"`
}

// @Summary Update dataset column descriptions
// @Description Update column descriptions for an existing dataset
// @ID update-dataset-column-descriptions
// @Tags datasets
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID"
// @Param body body updateColumnDescriptionsParams true "Column descriptions to update"
// @Success 200 {object} responses.SuccessResponse{data=models.DatasetSummaryWithName}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/datasets/{datasetID}/column-descriptions [patch]
func (h *httpHandler) updateColumnDescriptions(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	var body updateColumnDescriptionsParams
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body format",
			"code":    fiber.StatusBadRequest,
		})
	}

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

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

	// Get the current dataset summary from OLAP
	datasetSummary, err := h.olapSvc.GetDatasetSummary(dataset.Name)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	if datasetSummary == nil {
		return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "Dataset summary not found",
			"message": "No summary exists for this dataset",
			"code":    fiber.StatusNotFound,
		})
	}

	// Update the column descriptions
	summaryMap := make(map[string]int)
	for i := range *datasetSummary {
		summaryMap[(*datasetSummary)[i].ColumnName] = i
	}

	updatedColumns := 0
	for colName, desc := range body.ColumnDescriptions {
		if idx, exists := summaryMap[colName]; exists {
			(*datasetSummary)[idx].Description = desc
			updatedColumns++
		}
	}

	if updatedColumns == 0 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "No matching columns found",
			"message": "None of the provided column names match the dataset columns",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Delete existing summary first (if it exists) to avoid conflicts
	_ = h.datasetsSvc.DeleteDatasetSummary(dataset.Name)

	// Save the updated dataset summary
	updatedSummary, err := h.datasetsSvc.CreateDatasetSummary(dataset.Name, datasetSummary)
	if err != nil {
		h.logger.Error("Error updating dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Note: AI agent schema update should be triggered separately by the caller
	// if needed, as this handler doesn't have access to the AI agent service

	return ctx.JSON(map[string]*models.DatasetSummaryWithName{
		"data": updatedSummary,
	})
}
