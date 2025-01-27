package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) schema(ctx *fiber.Ctx) error {
	tableName := ctx.Params("tableName")

	schema, err := h.driverSvc.GetTableSchema(tableName)
	if err != nil {
		h.logger.Error("Error getting table schema", zap.Error(err))
		if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query",
				"code":    fiber.StatusBadRequest,
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
