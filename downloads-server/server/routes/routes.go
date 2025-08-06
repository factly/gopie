package routes

import (
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/postgres"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	store  *postgres.PostgresStore
	logger *logger.Logger
}

func Router(router fiber.Router, store *postgres.PostgresStore, logger *logger.Logger) {
	router.Get("/health", func(ctx *fiber.Ctx) error {
		return ctx.JSON("Ok")
	})
}
