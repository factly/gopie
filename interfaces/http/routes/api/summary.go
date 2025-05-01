package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

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
