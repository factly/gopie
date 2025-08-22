package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get dataset summary
// @Description Retrieves a summary of the specified dataset
// @Tags dataset
// @Accept json
// @Produce json
// @Param tableName path string true "Name of the table to get summary for"
// @Success 200 {object} map[string]interface{} "Dataset summary information"
// @Failure 404 {object} map[string]interface{} "Invalid query or table not found"
// @Failure 500 {object} map[string]interface{} "Internal server error"
// @Router /summary/{tableName} [get]
func (h *httpHandler) summary(ctx *fiber.Ctx) error {
	tableName := ctx.Params("tableName")

	summary, err := h.driverSvc.GetDatasetSummary(tableName)
	if err != nil {
		h.logger.Error("Error getting table schema", zap.Error(err))
		if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query",
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
		"summary": summary,
	})
}
