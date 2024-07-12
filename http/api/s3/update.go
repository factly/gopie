package s3

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type updateBody struct {
	Path      string `json:"path"`
	TableName string `json:"table_name"`
}

func (h *httpHandler) update(w http.ResponseWriter, r *http.Request) {
	var body updateBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	if body.Path == "" || body.TableName == "" {
		h.logger.Error("did not pass path or table_name")
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	err = h.conn.DropTable(context.Background(), body.TableName)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	const prefix = "s3://"

	if !strings.HasPrefix(body.Path, prefix) {
		h.logger.Error(fmt.Sprintf("invalid s3 path %s", body.Path))
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid s3 path", http.StatusBadRequest)))
		return
	}

	trimmed := strings.TrimPrefix(body.Path, prefix)
	parts := strings.SplitN(trimmed, "/", 2)

	if len(parts) < 2 {
		h.logger.Error(fmt.Sprintf("invalid s3 path %s", body.Path))
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid s3 path", http.StatusBadRequest)))
		return
	}

	bucket := parts[0]
	path := parts[1]

	err = h.objectStore.Transfer(context.Background(), map[string]any{
		"allow_schema_relaxation": false,
		"path":                    path,
	},
		map[string]any{"table": body.TableName},
		bucket,
	)

	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.NoObjectsFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusCreated, map[string]string{"message": fmt.Sprintf("updated duckdb file for '%s' as '%s'", body.Path, body.TableName)})
}
