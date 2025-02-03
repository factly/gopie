package projects

import "github.com/gofiber/fiber/v2"

func (h *httpHandler) delete(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	err := h.svc.Delete(projectID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.SendStatus(fiber.StatusNoContent)
}
