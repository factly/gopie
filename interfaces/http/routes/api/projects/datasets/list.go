package datasets

import (
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
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching datasets",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(datasets)
}
