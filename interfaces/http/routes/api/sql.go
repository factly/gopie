package api

import (
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type sqlRequestBody struct {
	Query string `json:"query"`
}

func (h *httpHandler) sql(ctx *fiber.Ctx) error {
	var body sqlRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return err
	}

	result, err := h.svc.Query(body.Query)
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))
		return err
	}

	return ctx.Status(fiber.StatusOK).JSON(result)
}
