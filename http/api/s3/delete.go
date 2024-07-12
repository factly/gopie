package s3

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type deleteBody struct {
	TableName string `json:"table_name"`
}

func (h *httpHandler) delete_(w http.ResponseWriter, r *http.Request) {

	var body deleteBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	err = h.conn.DropTable(context.Background(), body.TableName)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusCreated, map[string]string{"message": fmt.Sprintf("deleted table: '%s'", body.TableName)})
}
