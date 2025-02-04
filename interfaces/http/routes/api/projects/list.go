package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
)

func (h *httpHandler) list(ctx *fiber.Ctx) error {
	limitStr := ctx.Query("limit")
	pageStr := ctx.Query("page")
	query := ctx.Query("query")

	limit, page := pkg.ParseLimitAndPage(limitStr, pageStr)

	projects, err := h.svc.List(query, limit, page)
	if err != nil {
		if domain.IsStoreError(err) {
			switch err {
			case domain.ErrRecordNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "No projects found",
					"message": "No projects exist with the given criteria",
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
			"message": "Error fetching projects",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(projects)
}
