package apikeys

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type createRequestBody struct {
	Name        string `json:"name" validate:"required"`
	Description string `json:"description,omitempty"`
}

func (h *httpHandler) create(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)

	var body createRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
		})
	}

	if body.Name == "" {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "name is required",
			"message": "API key name is required",
		})
	}

	result, err := h.apikeyService.CreateAPIKey(ctx.Context(), models.CreateAPIKeyParams{
		Name:        body.Name,
		Description: body.Description,
		CreatedBy:   userID,
	})
	if err != nil {
		h.logger.Error("Error creating API key", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating API key",
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(result)
}
