package middleware

import (
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

// RequireAdmin rejects requests from non-admin users with 403 Forbidden.
func RequireAdmin() fiber.Handler {
	return func(c *fiber.Ctx) error {
		role, _ := c.Locals(RoleCtxKey).(models.Role)
		if role != models.Admin {
			return c.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"error":   "forbidden",
				"message": "Admin role required",
			})
		}
		return c.Next()
	}
}
