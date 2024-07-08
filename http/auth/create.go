package auth

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) create(w http.ResponseWriter, r *http.Request) {
	var m map[string]any

	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&m)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	// validate required fields
	if m["name"] == nil {
		h.logger.Error("name is a required field ")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("name is required field", http.StatusBadRequest)))
		return
	}

	if m["expiry"] == nil {
		m["expires_at"] = time.Now().Add(24 * time.Hour).Unix()
	} else {
		expiry, err := strconv.ParseInt(m["expiry"].(string), 10, 64)
		if err != nil {
			h.logger.Error("name is a required field ")
			errorx.Render(w, errorx.Parser(errorx.GetMessage("name is required field", http.StatusBadRequest)))
			return
		}
		m["expires_at"] = expiry
	}

	key, err := h.a.CreateKey(m)
	if err != nil {
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusCreated, key)
}
