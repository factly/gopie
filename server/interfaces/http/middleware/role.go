package middleware

import "github.com/gofiber/fiber/v2"

const RoleCtxKey = "role-ctx-key"

type Role string

const (
	Member Role = "member"
	Admin  Role = "admin"
)

func RoleAuthorization() fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Locals(RoleCtxKey, Member)
		return c.Next()
	}
}
