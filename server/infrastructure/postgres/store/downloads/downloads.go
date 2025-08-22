package downloads

import (
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PgDownloadsStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresDownloadsStore(db any, logger *logger.Logger) *PgDownloadsStore {
	return &PgDownloadsStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}
