package projects

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresProjectStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresProjectStore(db interface{}, logger *logger.Logger) repositories.ProjectStoreRepository {
	return &PostgresProjectStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}
