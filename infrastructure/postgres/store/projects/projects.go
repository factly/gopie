package projects

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
)

type PostgresProjectStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewPostgresProjectStore(q *gen.Queries, logger *logger.Logger) repositories.ProjectStoreRepository {
	return &PostgresProjectStore{
		q:      q,
		logger: logger,
	}
}
