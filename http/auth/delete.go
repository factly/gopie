package auth

import (
	"encoding/json"
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) delete_(w http.ResponseWriter, r *http.Request) {
	var body key

	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	if body.Key == "" {
		h.logger.Error("api_key is required field")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("api_key is required field", http.StatusBadRequest)))
		return
	}

	err = h.a.DeleteKey(body.Key)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusNoContent, nil)

}
