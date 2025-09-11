package apikeys

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresAPIKeyStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresAPIKeyStore(db any, logger *logger.Logger) repositories.APIKeyStoreRepository {
	return &PostgresAPIKeyStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}
