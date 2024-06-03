package api

import (
	"net/http"

	"github.com/factly/x/renderx"
)

func (h *httpHandler) healthHandler(w http.ResponseWriter, _ *http.Request) {
	renderx.JSON(w, http.StatusOK, "👍")
}
