package api

import (
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Query dataset using REST API
// @Description Query a dataset using REST-style parameters
// @Tags query
// @Accept json
// @Produce json
// @Param tableName path string true "Name of the dataset/table" example:"sales_data"
// @Param columns query string false "Comma-separated list of columns to return" example:"id,name,value"
// @Param sort query string false "Sort order (column name with optional -prefix for desc)" example:"-created_at"
// @Param limit query integer false "Number of records to return" example:"10"
// @Param page query integer false "Page number" example:"1"
// @Success 200 {array} map[string]interface{} "Query results"
// @Failure 400 {object} responses.ErrorResponse "Invalid query parameters"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/tables/{tableName} [get]
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

	result, err := h.driverSvc.RestQuery(params)
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
