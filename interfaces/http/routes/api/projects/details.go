package projects

import "github.com/gofiber/fiber/v2"

func (h *httpHandler) details(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	project, err := h.svc.Details(projectID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(project)
}
