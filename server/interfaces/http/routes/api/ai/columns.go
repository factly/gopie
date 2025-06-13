package ai

import (
	"fmt"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type genColumnsDescBody struct {
	Summary any `json:"summary"`
	Rows    any `json:"rows"`
}

func (h *httpHandler) genColumnsDesc(c *fiber.Ctx) error {
	body := new(genColumnsDescBody)
	if err := c.BodyParser(body); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	if body.Summary == nil || body.Rows == nil {
		return fiber.NewError(fiber.StatusBadRequest, "Summary and Rows are required")
	}

	rowsString := fmt.Sprintf("%v", body.Rows)
	SummaryString := fmt.Sprintf("%v", body.Summary)

	descriptions, err := h.aiSvc.GenerateColumnDescriptions(rowsString, SummaryString)
	if err != nil {
		h.logger.Error("Error generating column descriptions", zap.Error(err))
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to generate column descriptions")
	}

	return c.JSON(fiber.Map{
		"descriptions": descriptions,
	})
}
