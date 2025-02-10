package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
)

type updateProjectBody struct {
	Name        string `json:"name,omitempty" validate:"required,min=3,max=50"`
	Description string `json:"description,omitempty" validate:"omitempty,max=500"`
}

func (h *httpHandler) update(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	body := updateProjectBody{}
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	validate := validator.New()

	if err := validate.Struct(body); err != nil {
		var errors []models.ValidationError
		for _, err := range err.(validator.ValidationErrors) {
			errors = append(errors, models.ValidationError{
				Field: err.Field(),
				Tag:   err.Tag(),
				Value: err.Param(),
			})
		}
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   errors,
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})

	}

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
