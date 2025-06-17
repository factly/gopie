package ai

import (
	"fmt"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Description Request body for generating column descriptions using AI
type genColumnsDescBody struct {
	// Dataset summary information containing statistics about columns
	Summary any `json:"summary" validate:"required" example:"{\"column_name\": {\"type\": \"string\", \"count\": 1000}}"`
	// Sample rows from the dataset to help AI understand the data context
	Rows any `json:"rows" validate:"required" example:"[[\"value1\", \"value2\"], [\"value3\", \"value4\"]]"`
}

// @Summary Generate AI-powered column descriptions
// @Description Generate descriptive explanations for dataset columns using AI analysis of summary statistics and sample data
// @Tags ai
// @Accept json
// @Produce json
// @Param body body genColumnsDescBody true "Column description request parameters"
// @Success 200 {object} map[string]interface{} "Column descriptions generated successfully"
// @Failure 400 {object} map[string]interface{} "Invalid request body or missing required fields"
// @Failure 500 {object} map[string]interface{} "Failed to generate column descriptions"
// @Router /v1/api/ai/generate-column-descriptions [post]
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
