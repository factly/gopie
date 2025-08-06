package middleware

import (
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

const (
	UserCtxKey         = "x-user-id"
	OrganizationCtxKey = "x-organization-id"
)

func AuthorizeHeaders(logger *logger.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Extract user ID from the request context
		userID := c.Get(UserCtxKey)
		if userID == "" {
			logger.Error("User ID not found in request context")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "user ID not found",
			})
		}
		c.Locals(UserCtxKey, userID)

		orgID := c.Get(OrganizationCtxKey)
		if orgID == "" {
			logger.Error("Organization ID not found in request context", zap.String("userID", userID))
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "organization ID not found",
			})
		}
		c.Locals(OrganizationCtxKey, orgID)

		return c.Next()
	}
}
