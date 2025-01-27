package middleware

import (
	"strings"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func WithApiKeyAuth(validator repositories.ApiKeyRepository, logger *logger.Logger) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		key := ctx.Get("Authorization")
		if key == "" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Authorization header is missing",
				"code":    fiber.StatusUnauthorized,
			})
		}
		if strings.HasPrefix(key, "Bearer ") {
			key = key[7:]
		} else {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Invalid token",
				"code":    fiber.StatusUnauthorized,
			})
		}

		valid, err := validator.Validate(key)

		if !valid || err != nil {
			logger.Error("Error validating api key", zap.Error(err))
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"message": "Unauthorized",
				"error":   "Invalid token",
				"code":    fiber.StatusUnauthorized,
			})
		}

		return ctx.Next()
	}
}
