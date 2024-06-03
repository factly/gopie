package api

import (
	"encoding/json"
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type SqlRequestBody struct {
	Query string `json:"email"`
}

func (h *httpHandler) sql(w http.ResponseWriter, r *http.Request) {
	var body SqlRequestBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusOK, body)
}
