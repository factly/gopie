package projects

import (
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
)

// createRequestBody represents the request body for creating a project
// @Description Request body for creating a new project
type createRequestBody struct {
	// Name of the project
	Name string `json:"name" validate:"required,min=3,max=50" example:"My New Project"`
	// Description of the project
	Description string `json:"description" validate:"required,min=10,max=500" example:"This is a detailed description of my new project"`
}

// @Summary Create a new project
// @Description Create a new project with the given name and description
// @Tags projects
// @Accept json
// @Produce json
// @Param project body createRequestBody true "Project object"
// @Success 201 {object} responses.SuccessResponse{data=models.Project}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects [post]
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
