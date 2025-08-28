package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Get dataset summary
// @Description Retrieves a summary of the specified dataset from a chosen source.
// @Tags dataset
// @Accept json
// @Produce json
// @Param tableName path string true "Name of the table to get summary for"
// @Param source query string false "The data source: 'olap' for live query, 'oltp' for stored summary. Defaults to 'oltp'." Enums(olap, oltp)
// @Success 200 {object} map[string]interface{} "Dataset summary information"
// @Failure 400 {object} map[string]interface{} "Invalid source parameter"
// @Failure 404 {object} map[string]interface{} "Invalid query or table not found"
// @Failure 500 {object} map[string]interface{} "Internal server error"
// @Router /summary/{tableName} [get]
func (h *httpHandler) summary(ctx *fiber.Ctx) error {
	tableName := ctx.Params("tableName")
	source := ctx.Query("source", "oltp")

	var summary any
	var err error

	// 1. Select the correct service based on the source parameter.
	switch source {
	case "olap":
		// Assuming olapSvc is for OLAP source
		summary, err = h.olapSvc.GetDatasetSummary(tableName)
	case "oltp":
		// Assuming datasetsSvc is for OLTP (stored) source
		summary, err = h.datasetsSvc.GetDatasetSummary(tableName)
	default:
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid source parameter",
			"message": "Valid values are 'olap' or 'oltp'",
			"code":    fiber.StatusBadRequest,
		})
	}

	if err != nil {
		h.logger.Error("Error getting dataset summary", zap.Error(err), zap.String("source", source))
		if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query or table not found",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "An error occurred while getting the dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"summary": summary,
	})
}
