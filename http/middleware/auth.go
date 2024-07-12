package middleware

import (
	"errors"
	"net/http"
	"strings"

	"github.com/factly/x/errorx"
	"github.com/opentracing/opentracing-go/log"
)

func MasterKeyMiddleware(masterKey string) func(next http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			m, err := validAuthHeader(r)
			if err != nil {
				log.Error(err)
				errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusUnauthorized)))
				return
			}
			if m != masterKey {
				log.Error(errors.New("Invalid Master Key"))
				errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid Master Key", http.StatusUnauthorized)))
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func ApiKeyMiddleware(validate func(k string) (bool, error)) func(next http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			m, err := validAuthHeader(r)
			if err != nil {
				log.Error(err)
				errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusUnauthorized)))
				return
			}

			cond, err := validate(m)
			if err != nil {
				log.Error(err)
				errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid Api Key", http.StatusUnauthorized)))
				return
			}
			if !cond {
				errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid Api Key", http.StatusUnauthorized)))
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func validAuthHeader(r *http.Request) (string, error) {
	m := r.Header.Get("Authorization")
	parts := strings.Split(m, " ")
	if len(parts) != 2 {
		return "", errors.New("Invalid Authorization Header")
	}
	return parts[1], nil
}
