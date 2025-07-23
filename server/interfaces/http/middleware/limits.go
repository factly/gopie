package middleware

import "github.com/gofiber/fiber/v2"

const ImposeLimitsCtxKey = "impose-limits-ctx-key"

func ImposeLimit(value bool) fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Locals(ImposeLimitsCtxKey, value)
		return c.Next()
	}
}
