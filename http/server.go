package http

import (
	"fmt"
	"net/http"
	"time"

	"github.com/factly/gopie/ai"
	"github.com/factly/gopie/app"
	"github.com/factly/gopie/auth"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/http/api"
	"github.com/factly/gopie/http/api/s3"
	authApi "github.com/factly/gopie/http/auth"
	"github.com/factly/gopie/http/metrics"
	apiMiddleware "github.com/factly/gopie/http/middleware"
	s3Source "github.com/factly/gopie/source/s3"
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
		AllowedOrigins:   []string{"http://*"},
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

	masterKey := cfg.Auth.Mastkey

	iAuth := auth.NewAuth(cfg.Auth.BboltPath, logger, masterKey)

	conn := app.GetDuckDBConnection()
	openAiClient := ai.NewPortKeyClient(cfg.PortKey)

	objectStore := s3Source.NewS3Objectstore(logger, map[string]any{
		"aws_access_key_id":     cfg.S3.AccessKey,
		"aws_secret_access_key": cfg.S3.SecretAccessKey,
		"allow_host_access":     true,
		"aws_region":            "us-east-1",
		"aws_endpoint":          cfg.S3.Endpoint,
		"retain_files":          false,
	})

	objectStoreTranspoter := duckdb.NewObjectStoreToDuckDB(conn, logger, objectStore)
	// register api routes with api key validating middleware
	api.RegisterRoutes(router.With(apiMiddleware.ApiKeyMiddleware(iAuth.ValidateKey)).(*chi.Mux), logger, conn, openAiClient)
	// register auth routes with master_key validating middleware
	authApi.RegisterAuthRoutes(router.With(apiMiddleware.MasterKeyMiddleware(masterKey)).(*chi.Mux), logger, iAuth)
	// register metric routes with master_key validating middleware
	metrics.RegisterRoutes(router.With(apiMiddleware.MasterKeyMiddleware(masterKey)).(*chi.Mux), logger, conn)
	// register file upload routes with master_key validating middleware
	s3.RegisterRoutes(router.With(apiMiddleware.MasterKeyMiddleware(masterKey)).(*chi.Mux), logger, objectStoreTranspoter, conn)

	err := http.ListenAndServe(fmt.Sprintf(":%s", cfg.Server.Port), router)
	if err != nil {
		logger.Fatal(fmt.Sprintf("error starting Http Server: %s", err.Error()))
	}
}
