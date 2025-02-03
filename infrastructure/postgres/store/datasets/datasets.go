package datasets

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresDatasetStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresDatasetStore(db interface{}, logger *logger.Logger) repositories.DatasetStoreRepository {
	return &PostgresDatasetStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}
