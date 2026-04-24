package middleware

import (
	"strings"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func WithApiKeyAuth(service *services.ApikeyService, logger *logger.Logger) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		header := ctx.Get("Authorization")
		if header == "" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Authorization header is missing",
				"code":    fiber.StatusUnauthorized,
			})
		}
		key := header
		if strings.HasPrefix(header, "Bearer ") {
			key = header[7:]
		} else {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Invalid token format (expected Bearer)",
				"code":    fiber.StatusUnauthorized,
			})
		}
		hash := service.HashKey(key)

		// GetAPIKeyByHash filters out expired and revoked keys at the DB layer
		apiKey, err := service.GetAPIKeyByHash(ctx.Context(), hash)
		if err != nil || apiKey == nil {
			logger.Error("API key not found or error", zap.Error(err))
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Invalid API key",
				"code":    fiber.StatusUnauthorized,
			})
		}

		// Update last used timestamp asynchronously so it doesn't block the request
		go func() {
			if _, err := service.UpdateLastUsedAPIKey(ctx.Context(), apiKey.ID); err != nil {
				logger.Error("Failed to update API key last used", zap.Error(err))
			}
		}()

		ctx.Locals(UserCtxKey, apiKey.ID)
		ctx.Locals(OrganizationCtxKey, "system")
		ctx.Locals(RoleCtxKey, models.Admin)
		return ctx.Next()
	}
}
