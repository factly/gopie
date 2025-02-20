package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type updateDatasetParams struct {
	Description string `json:"description,omitempty"`
	Alias       string `json:"alias,omitempty"`
	UpdateBy    string `json:"update_by" validate:"required"`
}

// @Summary Update dataset
// @Description Update an existing dataset information
// @ID update-dataset
// @Tags Datasets
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID"
// @Param body body updateDatasetParams true "Dataset update parameters"
// @Success 200 {object} map[string]interface{} "Successfully updated dataset"
// @Failure 400 {object} fiber.Map "Invalid request body"
// @Failure 404 {object} fiber.Map "Dataset not found"
// @Failure 500 {object} fiber.Map "Internal server error"
// @Router /datasets/{datasetID} [put]
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")

	body := new(updateDatasetParams)
	if err := ctx.BodyParser(body); err != nil {
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
	_, err = h.datasetsSvc.Details(datasetID)
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
		Description: body.Description,
		Alias:       body.Alias,
		UpdatedBy:   body.UpdateBy,
	})

	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]*models.Dataset{
		"data": dataset,
	})
}
