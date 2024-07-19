package metrics

import (
	"context"
	"net/http"
	"strings"

	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) list_databases(w http.ResponseWriter, _ *http.Request) {
	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: "show databases"})
	if err != nil {
		h.logger.Error("error listing databases", "error", err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		h.logger.Error("error converting result to JSON", "error", err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	// filter json result
	// remove the suffix after second '_'
	// remove main_db from in values
	filteredRes := make([]string, 0)
	for _, i := range *jsonRes {
		if dbName, ok := i["database_name"].(string); ok {
			if dbName == "main_db" {
				continue
			}
			parts := strings.SplitN(dbName, "_", 3)
			if len(parts) > 2 {
				dbName = parts[0] + "_" + parts[1]
			}
			filteredRes = append(filteredRes, dbName)
		}
	}

	renderx.JSON(w, http.StatusOK, filteredRes)
}
