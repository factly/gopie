package auth

import (
	"encoding/json"
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) update(w http.ResponseWriter, r *http.Request) {
	var m struct {
		key
		Delta map[string]any `json:"delta"`
	}

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

	if m.Delta == nil {
		h.logger.Error("delta is required field")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("delta is required field", http.StatusBadRequest)))
		return
	}

	key, err := h.a.UpdateKey(m.Key, m.Delta)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusOK, key)
}

func (h *httpHandler) invalidate(w http.ResponseWriter, r *http.Request) {

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

	err = h.a.InvalidateKey(m.Key)

	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusNoContent, nil)

}
