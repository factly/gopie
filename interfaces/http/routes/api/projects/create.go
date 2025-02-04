package projects

import (
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

type createRequestBody struct {
	Name        string `json:"name" validate:"required,min=3,max=50"`
	Description string `json:"description" validate:"required,min=10,max=500"`
}

func (h *httpHandler) create(ctx *fiber.Ctx) error {
	body := ctx.Locals("body").(*createRequestBody)

	project, err := h.svc.Create(models.CreateProjectParams{
		Name:        body.Name,
		Description: body.Description,
	})

	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": project,
	})
}
