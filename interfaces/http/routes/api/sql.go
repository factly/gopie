package api

import (
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type sqlRequestBody struct {
	Query string `json:"query" validate:"required,min=1"`
}

func (h *httpHandler) sql(ctx *fiber.Ctx) error {
	var body sqlRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body format",
			"code":    fiber.StatusBadRequest,
		})
	}
	validate := validator.New()

	if err := validate.Struct(body); err != nil {
		var errors []models.ValidationError
		for _, err := range err.(validator.ValidationErrors) {
			errors = append(errors, models.ValidationError{
				Field: err.Field(),
				Tag:   err.Tag(),
				Value: err.Param(),
			})
		}
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   errors,
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})

	}

	result, err := h.driverSvc.SqlQuery(body.Query)
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))

		if domain.IsSqlError(err) {
			switch err {
			case domain.ErrTableNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   err.Error(),
					"message": "The requested dataset does not exist",
					"code":    fiber.StatusNotFound,
				})
			case domain.ErrNotSelectStatement:
				return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
					"error":   err.Error(),
					"message": "Only SELECT statements are allowed",
					"code":    fiber.StatusForbidden,
				})
			default:
				return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
					"error":   err.Error(),
					"message": "Invalid SQL query",
					"code":    fiber.StatusBadRequest,
				})
			}
		} else if strings.HasPrefix(err.Error(), "DuckDB") {
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Invalid query",
				"code":    fiber.StatusBadRequest,
			})
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Unknown error occurred while executing query",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(result)
}
