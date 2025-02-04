package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
)

func (h *httpHandler) list(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")
	limitStr := ctx.Query("limit")
	pageStr := ctx.Query("page")

	limit, page := pkg.ParseLimitAndPage(limitStr, pageStr)

	datasets, err := h.svc.List(projectID, limit, page)
	if err != nil {
		if domain.IsStoreError(err) {
			switch err {
			case domain.ErrRecordNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "No datasets found",
					"message": "No datasets exist for this project",
					"code":    fiber.StatusNotFound,
				})
			case domain.ErrInvalidData:
				return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
					"error":   "Invalid query parameters",
					"message": "The provided search parameters are invalid",
					"code":    fiber.StatusBadRequest,
				})
			}
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching datasets",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(datasets)
}
