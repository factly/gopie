package api

import (
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Query dataset using REST API
// @Description Query a dataset using REST-style parameters via POST body
// @Tags query
// @Accept json
// @Produce json
// @Param tableName path string true "Name of the dataset/table" example:"sales_data"
// @Param body body models.RestRequest true "Query parameters"
// @Success 200 {array} map[string]interface{} "Query results"
// @Failure 400 {object} responses.ErrorResponse "Invalid query parameters"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/tables/{tableName} [post]
func (h *httpHandler) rest(ctx *fiber.Ctx) error {
	table := ctx.Params("tableName")
	imposeLimits := ctx.Locals(middleware.ImposeLimitsCtxKey).(bool)

	var req models.RestRequest
	if len(ctx.Body()) > 0 {
		if err := ctx.BodyParser(&req); err != nil {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid request body",
				"code":    fiber.StatusBadRequest,
			})
		}
	}

	columns := req.Columns
	if len(columns) == 0 {
		columns = []string{"*"}
	}

	page := req.Page
	if page == 0 {
		page = 1
	}

	params := models.RestParams{
		Cols:         columns,
		Sort:         req.Sort,
		Limit:        req.Limit,
		Page:         page,
		Filter:       req.Filter,
		Table:        table,
		ImposeLimits: imposeLimits,
	}

	result, err := h.olapSvc.RestQuery(params)
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
