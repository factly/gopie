package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type nl2SqlRequestBody struct {
	Query     string `json:"query"`
	TableName string `json:"table_name"`
}

func (h httpHandler) nl2sql(w http.ResponseWriter, r *http.Request) {
	var body nl2SqlRequestBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}
	defer r.Body.Close()

	schema, err := getSchemaAsJson(h.conn, body.TableName)
	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.TableNotFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(fmt.Sprintf("Table with name %s is not found", body.TableName), http.StatusNotFound)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: fmt.Sprintf("SELECT * FROM %s ORDER BY RANDOM() LIMIT 20", body.TableName)})
	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.TableNotFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage("Table with given name is not found", http.StatusNotFound)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	first20Rows, err := res.RowsToMap()
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	content := fmt.Sprintf(`
    NATURAL LANGUAGE TO SQL CONVERSION \n
		TABLE_NAME: %s \n
	  QUERY: %s 
		SCHEMA: %s
		FIRST 20 ROWS: %s
		NOTE: 
		 1. RETURN ONLY SQL AND NOTHING ELSE. THE SCHEMA IS THE DESCRIPTION THE TABLE. ALWAYS USE DOUBLE QUOTES FOR THE TABLES AND COLUMNS NAMES IN SQL AND USE SINGLE QUOTES FOR VALUES IF THE "column_type" IS SIMILAR TO STRING
	   2. DONT SEND RESPONSES WITH PATTERN LIKE "QUERY: SELECT * FROM TABLE", "SQL: SELECT * FROM TABLE" THIS ARE INVALID. VALID RESPONSES PATTERNS ARE "SELECT * FROM TABLE", "SELECT * FROM TABLE WHERE COL = VAL"
	   3. QUERY IS THE NATURAL LANGUAGE TEXT YOU SHOULD CONVERT THAT INTO SQL
		`, body.TableName, body.Query, schema, first20Rows)

	sql, err := h.openAIClient.Complete(context.Background(), content)

	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, sql)

}
