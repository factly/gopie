package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
)

func (h *httpHandler) details(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	project, err := h.svc.Details(projectID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Project not found",
				"message": "The requested project does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(project)
}
