package auth

import (
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) details(w http.ResponseWriter, r *http.Request) {

	key := r.Header.Get("API_KEY")
	if key == "" {
		h.logger.Error("Header 'API_KEY' is not sent")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Header 'API_KEY' is not sent", http.StatusBadRequest)))
		return
	}

	k, err := h.a.GetKeyDetails(key)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	renderx.JSON(w, http.StatusOK, k)
}
