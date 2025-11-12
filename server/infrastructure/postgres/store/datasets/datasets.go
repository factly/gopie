package datasets

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PgDatasetStore struct {
	db     *pgxpool.Pool
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresDatasetStore(db any, logger *logger.Logger) repositories.DatasetStoreRepository {
	return &PgDatasetStore{
		db:     db.(*pgxpool.Pool),
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}

func (store *PgDatasetStore) GetDB() any {
	return store.db
}
