package api

import (
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/factly/gopie/pkg/duckdbsql"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type nl2SqlRequestBody struct {
	Query     string `json:"query"`
	TableName string `json:"table_name"`
}

// Function to convert schema to JSON
func convertSchemaToJSON(schema interface{}) string {
	schemaJSON, err := json.Marshal(schema)
	if err != nil {
		log.Fatal("Error marshalling schema to JSON:", err)
	}
	return string(schemaJSON)
}

// Function to convert random rows to CSV
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

func (h httpHandler) nl2sql(w http.ResponseWriter, r *http.Request) {
	var body nl2SqlRequestBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.handleError(w, err, "error decoding body: "+err.Error(), http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	if body.Query == "get all data" {
		sql := map[string]string{
			"sql": fmt.Sprintf("select * from %s", body.TableName),
		}
		renderx.JSON(w, http.StatusOK, sql)
		return
	}

	_, err = duckdbsql.Parse(body.Query)

	if err == nil {
		sql := map[string]string{
			"sql": body.Query,
		}
		renderx.JSON(w, http.StatusOK, sql)
		return
	}

	schemaRes, err := h.executeQuery(fmt.Sprintf("DESC %s", body.TableName), body.TableName)
	if err != nil {
		h.handleError(w, err, "error executing schema query", http.StatusInternalServerError)
		return
	}

	schema, err := schemaRes.RowsToMap()
	if err != nil {
		h.handleError(w, err, "error converting result to JSON", http.StatusInternalServerError)
		return
	}

	randomNRowsRes, err := h.executeQuery(fmt.Sprintf("SELECT * FROM %s ORDER BY RANDOM() LIMIT 50", body.TableName), body.TableName)
	if err != nil {
		h.handleError(w, err, "error getting random rows: "+err.Error(), http.StatusInternalServerError)
		return
	}

	randomNRows, err := randomNRowsRes.RowsToMap()
	if err != nil {
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	// Dereference the pointer to randomNRows
	schemaJSON := convertSchemaToJSON(schema)
	rowsCSV := convertRowsToCSV(*randomNRows)

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
		`, body.Query, body.TableName, schemaJSON, rowsCSV)

	sql, err := h.openAIClient.Complete(context.Background(), content)

	if err != nil {
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	params := ingestEventParams{
		subject:  r.Header.Get("x-gopie-organisation-id"),
		dataset:  body.TableName,
		userID:   r.Header.Get("x-gopie-user-id"),
		method:   r.Method,
		endpoint: r.URL.String(),
	}
	ingestEvent(h.metering, params)

	renderx.JSON(w, http.StatusOK, sql)
}
