package middleware

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
)

type ValidationError struct {
	Field string `json:"field"`
	Tag   string `json:"tag"`
	Value string `json:"value"`
}

func ValidateReqBodyMiddleware(model interface{}) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		obj := model

		if err := ctx.BodyParser(&obj); err != nil {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid request body",
				"code":    fiber.StatusBadRequest,
			})
		}

		validate := validator.New()

		if err := validate.Struct(obj); err != nil {
			var errors []ValidationError
			for _, err := range err.(validator.ValidationErrors) {
				errors = append(errors, ValidationError{
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

		ctx.Locals("body", obj)
		return ctx.Next()
	}
}

// ValidateProjectMiddleware checks if a project exists before proceeding with dataset operations
func ValidateProjectMiddleware(projectSvc *services.ProjectService) fiber.Handler {
	return func(c *fiber.Ctx) error {
		projectID := c.Params("projectID")
		_, err := projectSvc.Details(projectID)
		if err != nil {
			if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
				return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "Project not found",
					"message": "The requested project does not exist",
					"code":    fiber.StatusNotFound,
				})
			}
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error validating project",
				"code":    fiber.StatusInternalServerError,
			})
		}
		return c.Next()
	}
}
