package auth

import (
	"encoding/json"
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) details(w http.ResponseWriter, r *http.Request) {
	var m key

	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&m)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	if m.Key == "" {
		h.logger.Error("api_key is required field")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("api_key is required field", http.StatusBadRequest)))
		return
	}

	key, err := h.a.GetKeyDetails(m.Key)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusOK, key)
}
