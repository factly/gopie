package middleware

import (
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/zitadel"
	"github.com/gofiber/adaptor/v2"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// Zitadel returns a fiber.Handler that uses the Zitadel interceptor to authorize requests.
func ZitadelAuthorizer(logger *logger.Logger) fiber.Handler {
	logger.Info("Setting up Zitadel authorizer middleware")
	return adaptor.HTTPMiddleware(zitadel.ZitadelInterceptor.RequireAuthorization())
}

const (
	UserCtxKey         = "x-user-id"
	OrganizationCtxKey = "x-organization-id"
)

// setup auth-ctx from zitadel interceptor as x-user-id and x-organization-id
// This middleware must be used after ZitadelAuthorizer to access the auth context
func SetupZitadelAuthCtx(logger *logger.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Extract auth context set by Zitadel interceptor
		authCtx := zitadel.ZitadelInterceptor.Context(c.Context())
		logger.Error("Auth context cannot be nil", zap.Any("authCtx", authCtx))
		if authCtx == nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "unauthorized",
			})
		}

		// Set user ID and organization ID in the context
		userID := authCtx.UserID()
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

func SetupApiServerAuthCtx(logger *logger.Logger) fiber.Handler {
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
