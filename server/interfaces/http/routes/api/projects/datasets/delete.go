package datasets

import (
	"errors"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
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
	projectID := ctx.Params("projectID")

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

	// we don't have to wait till the schema is delete on the aiagent
	go func() {
		h.logger.Info("Delete database schema from aiagent..")
		err := h.aiAgentSvc.DeleteSchema(&models.SchemaParams{
			ProjectID: projectID,
			DatasetID: dataset.ID,
		})
		if err != nil {
			h.logger.Error("Failed to delete schema from aiagent", zap.Error(err))
			err = retryDeleteSchema(h.aiAgentSvc, h.logger, (&models.SchemaParams{
				ProjectID: projectID,
				DatasetID: dataset.ID,
			}))
			if err != nil {
				h.logger.Error("Failed to delete schema after 3 retries please delete manually for dataset",
					zap.String("datasetID", dataset.ID))
			}
		}
	}()

	return ctx.SendStatus(fiber.StatusNoContent)
}

func retryDropTable(h *httpHandler, datasetName string) error {
	for range 3 {
		err := h.olapSvc.DropTable(datasetName)
		if err == nil {
			return nil
		}
		h.logger.Warn("Retrying to drop OLAP table", zap.Error(err), zap.String("datasetName", datasetName))
	}

	return errors.New("failed to drop OLAP table after retries")
}

func retryDeleteSchema(svc *services.AIService, logger *logger.Logger, params *models.SchemaParams) error {
	for range 3 {
		err := svc.DeleteSchema(params)
		if err == nil {
			return nil
		}

		logger.Warn("Retrying to delete schema", zap.Error(err))
	}
	return errors.New("Failed to delete schema")
}
