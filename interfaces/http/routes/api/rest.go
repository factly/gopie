package api

import (
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) rest(ctx *fiber.Ctx) error {
	table := ctx.Params("tableName")

	columns := strings.Split(ctx.Query("columns", "*"), ",")
	filters := ctx.Queries()
	sort := ctx.Query("sort", "")
	limit := ctx.QueryInt("limit")
	page := ctx.QueryInt("page", 1)

	params := models.RestParams{
		Cols:   columns,
		Sort:   sort,
		Limit:  limit,
		Page:   page,
		Filter: filters,
		Table:  table,
	}

	result, err := h.svc.RestQuery(params)
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))

		if domain.IsSqlError(err) {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query",
				"code":    fiber.StatusBadRequest,
			})
		} else if domain.IsRestParamsError(err) {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid rest params",
				"code":    fiber.StatusBadRequest,
			})
		} else if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query",
				"code":    fiber.StatusBadRequest,
			})
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Unknown error occurred while executing query",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(result)
}
