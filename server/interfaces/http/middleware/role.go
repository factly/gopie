package middleware

import (
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
)

const RoleCtxKey = "role-ctx-key"

func RoleAuthorization() fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Locals(RoleCtxKey, models.Member)
		return c.Next()
	}
}
