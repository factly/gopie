package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"strings"

	"github.com/factly/x/renderx"
)

type sqlRequestBody struct {
	Query string `json:"query"`
}

func (h *httpHandler) sql(w http.ResponseWriter, r *http.Request) {
	var body sqlRequestBody

	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.handleError(w, err, "error decoding body", http.StatusBadRequest)
		return
	}

	query := imposeLimits(body.Query)

	table, err := extractTableName(query)
	if err != nil {
		h.handleError(w, err, "error extracting table name", http.StatusBadRequest)
		return
	}

	res, err := h.executeQuery(query, table)
	if err != nil {
		h.handleError(w, err, "error executing query", http.StatusInternalServerError)
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		h.handleError(w, err, "error converting result to JSON", http.StatusInternalServerError)
		return
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

func extractTableName(query string) (string, error) {
	// Regular expression to match "FROM table_name" or 'FROM "table name"'
	re := regexp.MustCompile(`(?i)\bFROM\s+(?:([a-zA-Z0-9_]+)|"([^"]*)")`)

	matches := re.FindStringSubmatch(query)
	if len(matches) < 2 {
		return "", fmt.Errorf("no table name found in query")
	}

	// If the first capture group is empty, use the second (quoted) group
	if matches[1] != "" {
		return matches[1], nil
	}
	return strings.Replace(matches[2], `\"`, `"`, -1), nil
}
