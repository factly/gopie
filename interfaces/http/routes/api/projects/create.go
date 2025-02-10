package projects

import (
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
)

type createRequestBody struct {
	Name        string `json:"name" validate:"required,min=3,max=50"`
	Description string `json:"description" validate:"required,min=10,max=500"`
}

func (h *httpHandler) create(ctx *fiber.Ctx) error {
	body := createRequestBody{}
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
