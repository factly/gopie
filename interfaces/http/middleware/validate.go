package middleware

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
)

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
