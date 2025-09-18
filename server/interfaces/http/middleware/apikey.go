package middleware

import (
	"strings"

	"github.com/factly/gopie/application/services"
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
		// Hash the incoming API key
		hash := service.HashKey(key)

		// No need to check for expiry or revoked status as GetAPIKeyByHash does that on the database layer itself
		apiKey, err := service.GetAPIKeyByHash(ctx.Context(), hash)
		if err != nil || apiKey == nil {
			logger.Error("API key not found or error", zap.Error(err))
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Invalid API key",
				"code":    fiber.StatusUnauthorized,
			})
		}

		// set apikey as user in context for further use
		ctx.Locals(UserCtxKey, apiKey.ID)
		ctx.Locals(OrganizationCtxKey, apiKey.OrgID)
		return ctx.Next()
	}
}
