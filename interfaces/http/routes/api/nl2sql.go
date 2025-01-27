package api

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type nl2SqlRequest struct {
	Query     string `json:"query"`
	TableName string `json:"table"`
}

func convertSchemaToJson(schema any) string {
	schemaJson, _ := json.Marshal(schema)
	return string(schemaJson)
}

func convertRowsToCSV(rows []map[string]interface{}) string {
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

func (h *httpHandler) nl2sql(ctx *fiber.Ctx) error {
	var body nl2SqlRequest
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	if body.Query == "get all data" {
		sql := map[string]string{
			"query": "select * from " + body.TableName,
		}
		return ctx.Status(fiber.StatusOK).JSON(sql)
	}

	schemaRes, err := h.driverSvc.GetTableSchema(body.TableName)
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))
		if strings.HasPrefix(err.Error(), "DuckDB") {
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

	randomNRows, err := h.driverSvc.ExecuteQuery(fmt.Sprintf("select * from %s order by random() limit 50", body.TableName))
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Unknown error occurred while executing query",
			"code":    fiber.StatusInternalServerError,
		})
	}

	schemaJson := convertSchemaToJson(schemaRes)
	rowsCsv := convertRowsToCSV(randomNRows)

	content := fmt.Sprintf(`
    You are a DuckDB expert. Given the query in natural language, create a syntactically correct DuckDB query to run.

	QUERY IN NATURAL LANGUAGE: %s 

	TABLE NAME: %s

	TABLE SCHEMA IN JSON: 
	
	---------------------
	%s
	---------------------

	RANDOM 50 ROWS IN CSV: 
	
	---------------------
	%s
	---------------------

	NOTE: 
	- IMP: Return only an syntactially correct DuckDB SQL and nothing else
	- Do not end the statement with a semicolon ';' 
	- Do not wrap the response in code blocks or quotes
	- Always use double quotes for the table and column names in SQL and use single quotes for values
	- Do not send responses with patterns like "query: select * from table", "sql: select * from table" these are invalid. Valid response patterns are "select * from table", "select * from table where col = val"
	- Use Table Schema provided in JSON to understand the columns and their data types
	- Use Random 50 Rows provided in CSV to understand the data in the table. This is not complete data, just a sample of 50 rows to understand the data in the table. Use your understanding of the data to write the query.
	- The data has 'All India' with totals for all states as a part of 'state' column. This should be excluded from queries when filtering on 'state' column or aggregating data based on 'state' column.
	- If user asks for 'share' of column, it means the percentage of the column value in the total of the column. For example, if user asks for 'share of sales', it means the percentage of sales in the total sales.
	- In some datasets 'Total' is part of categorical columns. Calculations go wrong in such cases. Please exclude 'Total' from calculations for all categorical fields in the queries. 
	- Most tables have 'units' or 'unit' column which is explanation of the value columns in the row. Eg content for units: 'value in absolute number', 'amount_spent in rupees', 'capital in rupees, exports in percentage' where 'value', 'amount_spent, 'capital', 'exports' are column names. 
	- Add 'units'/'unit' to the query output when displaying counts from the value columns like 'value', 'amount_spent', 'capital', 'exports' in the above example.
	- When the user specifically asks for similar or approximate matches in string comparisons, use Levenshtein distance.
	- Use ILIKE for case-insensitive string matching.
	- String only generate SQL for read queries nothing else.
		`, body.Query, body.TableName, schemaJson, rowsCsv)

	sql, err := h.aiSvc.GenerateSql(content)
	if err != nil {
		h.logger.Error("Error executing query", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Unknown error occurred generating SQL",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"sql": sql,
	})
}
