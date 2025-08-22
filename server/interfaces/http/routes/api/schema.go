package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get table schemas
// @Description Get the schemas information for a dataset/table
// @Tags query
// @Accept json
// @Produce json
// @Param tableName path string true "Name of the dataset/table" example:"sales_data"
// @Success 200 {object} map[string]interface{} "Schema information"
// @Failure 400 {object} responses.ErrorResponse "Invalid table name"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/schemas/{tableName} [get]
func (h *httpHandler) schemas(ctx *fiber.Ctx) error {
	tableName := ctx.Params("tableName")

	schema, err := h.driverSvc.GetTableSchema(tableName)
	if err != nil {
		h.logger.Error("Error getting table schema", zap.Error(err))
		if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Dataset not found",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Unknown error occurred while getting table schema",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"schema": schema,
	})
}
