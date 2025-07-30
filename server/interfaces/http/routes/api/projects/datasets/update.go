package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type updateDatasetParams struct {
	Description  string `json:"description,omitempty"`
	Alias        string `json:"alias,omitempty"`
	CustomPrompt string `json:"custom_prompt"`
}

// @Summary Update dataset
// @Description Update an existing dataset information
// @ID update-dataset
// @Tags datasets
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID"
// @Param body body updateDatasetParams true "Dataset update parameters"
// @Success 200 {object} responses.SuccessResponse{data=models.Dataset}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID}/datasets/{datasetID} [put]
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	projectID := ctx.Params("projectID")
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	var body updateDatasetParams
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
	existingDataset, err := h.datasetsSvc.Details(datasetID, orgID)
	if err != nil {
		h.logger.Error("Error updating dataset", zap.Error(err), zap.String("datasetID", datasetID))
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

	dataset, err := h.datasetsSvc.Update(datasetID, &models.UpdateDatasetParams{
		Description:  body.Description,
		Alias:        body.Alias,
		UpdatedBy:    userID,
		Columns:      existingDataset.Columns,
		FilePath:     existingDataset.FilePath,
		RowCount:     existingDataset.RowCount,
		Size:         existingDataset.Size,
		OrgID:        orgID,
		CustomPrompt: body.CustomPrompt,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: dataset.ID,
		ProjectID: projectID,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading schema",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]*models.Dataset{
		"data": dataset,
	})
}
