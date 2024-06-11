package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type SqlRequestBody struct {
	Query string `json:"query"`
}

func (h *httpHandler) sql(w http.ResponseWriter, r *http.Request) {
	var body SqlRequestBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: body.Query})

	if err != nil {
		fmt.Println(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	var data []map[string]any

	for res.Rows.Next() {
		d := make(map[string]any)
		err = res.MapScan(d)
		if err != nil {
			fmt.Println(err.Error())
			errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
			return
		}

		data = append(data, d)
	}

	renderx.JSON(w, http.StatusOK, data)
}
