package chats

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// chatRequestBody represents the request body for chat interaction
// @Description Request body for creating or continuing a chat conversation
type chatRequestBody struct {
	// Unique identifier of an existing chat (optional for new chats)
	ChatID string `json:"chat_id" validate:"omitempty,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// ID of the dataset to analyze
	DatasetID string `json:"dataset_id" validate:"omitempty,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// User ID of the creator
	CreatedBy string `json:"created_by" validate:"omitempty" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Array of chat messages
	Messages []struct {
		// Message content
		Content string `json:"content" validate:"required" example:"Show me the total sales by region"`
		// Message role (user/assistant)
		Role string `json:"role" validate:"required" example:"user"`
	} `json:"messages" validate:"required"`
}

// @Summary Create or continue chat
// @Description Create a new chat or continue an existing chat conversation with AI about a dataset
// @Tags chats
// @Accept json
// @Produce json
// @Param body body chatRequeryBody true "Chat request parameters"
// @Success 201 {object} responses.SuccessResponse{data=models.ChatWithMessages} "Chat created/continued successfully"
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/chats [post]
func (h *httpHandler) chat(ctx *fiber.Ctx) error {
	body := chatRequestBody{}
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	if len(body.Messages) == 0 {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "messages field is required",
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}
	body.Messages[len(body.Messages)-1].Role = "user"

	dataset, err := h.datasetSvc.Details(body.DatasetID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Dataset not found",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	schemaRes, err := h.olapSvc.GetTableSchema(dataset.Name)
	if err != nil {
		h.logger.Error("Error getting table schema", zap.Error(err))
		if strings.Contains(err.Error(), "does not exist") {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   domain.ErrTableNotFound.Error(),
				"message": fmt.Sprintf("Table '%s' not found", dataset.Name),
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating table",
			"code":    fiber.StatusInternalServerError,
		})
	}

	randomNRows, err := h.olapSvc.ExecuteQuery(fmt.Sprintf("select * from %s order by random() limit 50", dataset.Name))
	if err != nil {
		h.logger.Error("Error fetching sample data", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching sample data from table",
			"code":    fiber.StatusInternalServerError,
		})
	}

	schemaJson := convertSchemaToJson(schemaRes)
	rowsCsv := convertRowsToCSV(randomNRows)

	prompt := fmt.Sprintf(`
    You are a DuckDB and data expert. Review the user's question and respond appropriately:

    1. For SQL queries, format your response as:
    ---SQL---
    <SQL query here without semicolon>
    ---SQL---

    2. For non-SQL responses (like general questions), format as:
    ---TEXT---
    <Your response here>
    ---TEXT---

	USER QUESTION: %s 

	TABLE NAME: %s

	TABLE SCHEMA IN JSON: 
	---------------------
	%s
	---------------------

	RANDOM 50 ROWS IN CSV: 
	---------------------
	%s
	---------------------

	RULES FOR SQL QUERIES:
	- No semicolon at end of query
	- Use double quotes for table/column names, single quotes for values
	- Exclude rows with state='All India' when filtering/aggregating by state 
	- For share/percentage calculations, calculate as: (value/total)*100
	- Exclude 'Total' category from categorical field calculations
	- Include units/unit column when displaying value columns
	- Use Levenshtein for fuzzy string matching
	- Use ILIKE for case-insensitive matching
	- Generate only read queries (SELECT)
		`, body.Messages[len(body.Messages)-1].Content, dataset.Name, schemaJson, rowsCsv)

	messages := make([]models.ChatMessage, 0, len(body.Messages))
	for _, m := range body.Messages {
		messages = append(messages, models.ChatMessage{
			Content: m.Content,
			Role:    m.Role,
		})
	}

	chatWithMessages, err := h.chatSvc.ChatWithAi(&models.ChatWithAiParams{
		ChatID:    body.ChatID,
		DatasetID: body.DatasetID,
		CreatedBy: body.CreatedBy,
		Messages:  messages,
		Prompt:    prompt,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error chating with AI",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": chatWithMessages,
	})
}

func convertSchemaToJson(schema any) string {
	schemaJson, _ := json.Marshal(schema)
	return string(schemaJson)
}

func convertRowsToCSV(rows []map[string]any) string {
	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)

	// Write CSV headers (column names)
	if len(rows) > 0 {
		headers := make([]string, 0, len(rows[0]))
		for key := range rows[0] {
			headers = append(headers, key)
		}
		writer.Write(headers)

		// Write CSV data rows
		for _, row := range rows {
			record := make([]string, 0, len(row))
			for _, value := range row {
				record = append(record, fmt.Sprintf("%v", value))
			}
			writer.Write(record)
		}
	}

	writer.Flush()
	return buf.String()
}
