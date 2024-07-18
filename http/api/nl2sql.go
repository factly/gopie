package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

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
		h.handleError(w, err, "error decoding body: "+err.Error(), http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	schemaRes, err := h.executeQuery(fmt.Sprintf("DESC %s", body.TableName), body.TableName)
	if err != nil {
		h.handleError(w, err, "error executing schema query", http.StatusInternalServerError)
		return
	}

	schema, err := schemaRes.RowsToMap()
	if err != nil {
		h.handleError(w, err, "error converting resutl to JSON", http.StatusInternalServerError)
		return
	}

	first20RowsRes, err := h.executeQuery(fmt.Sprintf("SELECT * FROM %s ORDER BY RANDOM() LIMIT 20", body.TableName), body.TableName)
	if err != nil {
		h.handleError(w, err, "error getting random rows: "+err.Error(), http.StatusInternalServerError)
		return
	}

	first20Rows, err := first20RowsRes.RowsToMap()
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
		RANDOM 20 ROWS: %s
		NOTE: 
		 1. RETURN ONLY SQL AND NOTHING ELSE. THE SCHEMA IS THE DESCRIPTION THE TABLE. ALWAYS USE DOUBLE QUOTES FOR THE TABLES AND COLUMNS NAMES IN SQL AND USE SINGLE QUOTES FOR VALUES
	   2. DONT SEND RESPONSES WITH PATTERN LIKE "QUERY: SELECT * FROM TABLE", "SQL: SELECT * FROM TABLE" THESE ARE INVALID. VALID RESPONSES PATTERNS ARE "SELECT * FROM TABLE", "SELECT * FROM TABLE WHERE COL = VAL"
	   3. QUERY IS THE NATURAL LANGUAGE TEXT YOU SHOULD CONVERT THAT INTO SQL
	   4. DONOT END THE STATEMENT WITH A SEMI-COLON i.e. ';'
		`, body.TableName, body.Query, schema, first20Rows)

	sql, err := h.openAIClient.Complete(context.Background(), content)

	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, sql)

}
