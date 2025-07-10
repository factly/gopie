package database

import (
	"strconv"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary List database sources
// @Description Get a list of all database sources with pagination
// @Tags database
// @Accept json
// @Produce json
// @Param limit query int false "Limit number of results" default(20)
// @Param page query int false "Page number" default(1)
// @Success 200 {object} responses.SuccessResponse{data=[]models.DatabaseSource} // TODO: Update to use PaginationView
// @Failure 400 {object} responses.ErrorResponse "Invalid query parameters"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database [get]
func (h *httpHandler) list(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	pageStr := ctx.Query("page", "1")
	limitStr := ctx.Query("limit", strconv.Itoa(models.DefaultLimit))

	page, err := strconv.Atoi(pageStr)
	if err != nil || page < 1 {
		h.logger.Error("Invalid page parameter", zap.Error(err), zap.String("page", pageStr))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid page parameter",
			"message": "Page must be a positive integer",
			"code":    fiber.StatusBadRequest,
		})
	}

	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit < 1 {
		h.logger.Error("Invalid limit parameter", zap.Error(err), zap.String("limit", limitStr))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Invalid limit parameter",
			"message": "Limit must be a positive integer",
			"code":    fiber.StatusBadRequest,
		})
	}

	offset := (page - 1) * limit

	sources, err := h.dbSourceSvc.List(limit, offset, orgID)
	if err != nil {
		h.logger.Error("Error listing database sources", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error listing database sources",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"data":  sources,
		"page":  page,
		"limit": limit,
	})
}
