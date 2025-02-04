package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

type updateProjectBody struct {
	Name        string `json:"name,omitempty" validate:"required,min=3,max=50"`
	Description string `json:"description,omitempty" validate:"omitempty,max=500"`
}

func (h *httpHandler) update(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	body := ctx.Locals("body").(*updateProjectBody)

	project, err := h.svc.Update(projectID, &models.UpdateProjectParams{
		Name:        body.Name,
		Description: body.Description,
	})
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
			"message": "Error updating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": project,
	})
}
