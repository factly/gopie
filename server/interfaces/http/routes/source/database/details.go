package database

import (
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Check for timestamp column
// @Description Checks whether the given dataset has a timestamp column for incremental updates
// @Tags database
// @Accept json
// @Produce json
// @Param datasetID path string true "Dataset ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} map[string]bool{"has_timestamp_column":true}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/refresh/{datasetID} [get]
func (h *httpHandler) hasTimestampColumn(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	d := ctx.Params("datasetID")

	has, err := h.dbSourceSvc.HasTimestampColumn(d, orgID)
	if err != nil {
		h.logger.Error("Error checking timestamp column", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Internal server error",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"has_timestamp_column": has,
	})
}
