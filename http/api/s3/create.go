package s3

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/pkg"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type createBody struct {
	Path string `json:"path"`
}

func (h *httpHandler) create(w http.ResponseWriter, r *http.Request) {
	var body createBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
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

	tableName := fmt.Sprintf("gp_%s", pkg.RandomString(12))

	err = h.objectStore.Transfer(context.Background(), map[string]any{
		"allow_schema_relaxation": false,
		"path":                    path,
	},
		map[string]any{"table": tableName},
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

	renderx.JSON(w, http.StatusCreated, map[string]string{"message": fmt.Sprintf("created duckdb file for '%s' as '%s'", body.Path, tableName), "tableName": tableName})
}
