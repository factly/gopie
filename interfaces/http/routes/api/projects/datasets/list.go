package datasets

import (
	"errors"

	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (h *httpHandler) list(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")
	limitStr := ctx.Query("limit")
	pageStr := ctx.Query("page")

	limit, page := pkg.ParseLimitAndPage(limitStr, pageStr)

	datasets, err := h.svc.List(projectID, limit, page)
	if err != nil {
		h.logger.Error("Error fetching datasets", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "No datasets found",
				"message": "No datasets exist for this project",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching datasets",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(datasets)
}
