package middleware

import (
	"net/http"

	"github.com/factly/x/errorx"
)

func NilPointerMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				errorx.Render(w, errorx.Parser(errorx.GetMessage("internal server error", http.StatusInternalServerError)))
			}
		}()
		next.ServeHTTP(w, r)
	})
}
