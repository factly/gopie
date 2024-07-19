package s3

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

func (h *httpHandler) detach(w http.ResponseWriter, r *http.Request) {
	var body deleteBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	err = h.conn.DetachTable(context.Background(), body.TableName)
	if err != nil {

		h.logger.Error(err.Error())
		if err == custom_errors.TableNotFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusNotFound)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, map[string]string{"message": fmt.Sprintf("detached table: '%s'", body.TableName)})
}
