package auth

import (
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) list(w http.ResponseWriter, r *http.Request) {
	queries := r.URL.Query()
	m := make(map[string]string)

	for key, val := range queries {
		if len(val) > 0 {
			m[key] = val[0]
		}
	}

	keys, err := h.a.ListKeys(m)

	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, keys)
}
