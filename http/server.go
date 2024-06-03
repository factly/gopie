package http

import (
	"fmt"
	"net/http"
	"time"

	"github.com/factly/gopie/app"
	"github.com/factly/gopie/http/api"
	apiMiddleware "github.com/factly/gopie/http/middleware"
	"github.com/go-chi/chi/middleware"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/cors"
)

func RunHttpServer(app *app.App) {
	logger := app.GetLogger()
	cfg := app.GetConfig()

	logger.Info("🚀🚀 Starting HTTP server on port: " + cfg.Server.Port)
	router := chi.NewRouter()

	router.Use(cors.Handler(cors.Options{
		// AllowedOrigins:   []string{"https://foo.com"}, // Use this to allow specific origin hosts
		AllowedOrigins: []string{"http://*"},
		// AllowOriginFunc:  func(r *http.Request, origin string) bool { return true },
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-User", "X-Organisation"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: false,
		MaxAge:           300, // Maximum value not ignored by any of major browsers
	}))

	router.Use(middleware.RequestID)
	router.Use(middleware.RealIP)
	router.Use(logger.GetHTTPMiddleWare())
	router.Use(apiMiddleware.NilPointerMiddleware)
	router.Use(middleware.Timeout(5 * time.Minute))

	httpHandlerInitInput := api.HttpHandlerInitInput{Logger: *logger}
	api.RegisterRoutes(router, httpHandlerInitInput)

	err := http.ListenAndServe(fmt.Sprintf(":%s", cfg.Server.Port), router)
	if err != nil {
		logger.Fatal(fmt.Sprintf("error starting Http Server: %s", err.Error()))
	}
}
