package routes

import (
	"github.com/factly/gopie/downlods-server/duckdb"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/postgres"
	"github.com/factly/gopie/downlods-server/s3"
	"github.com/gofiber/fiber/v2"
)

// httpHandler holds the dependencies for your API handlers.
type httpHandler struct {
	dbStore       *postgres.PostgresStore
	olapStore     *duckdb.OlapDBDriver
	logger        *logger.Logger
	s3ObjectStore *s3.S3ObjectStore
}

func NewHttpHandler(db *postgres.PostgresStore, s3 *s3.S3ObjectStore, olap *duckdb.OlapDBDriver, log *logger.Logger) *httpHandler {
	return &httpHandler{
		dbStore:       db,
		s3ObjectStore: s3,
		logger:        log,
		olapStore:     olap,
	}
}

// RegisterRoutes sets up all the application routes on the provided fiber router.
func (h *httpHandler) RegisterRoutes(router fiber.Router) {
	router.Get("/health", h.healthCheck)
}

func (h *httpHandler) healthCheck(c *fiber.Ctx) error {
	return c.JSON("Ok")
}
