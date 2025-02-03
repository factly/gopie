package projects

import (
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
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching projects",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(projects)
}
