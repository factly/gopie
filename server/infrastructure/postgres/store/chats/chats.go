package chats

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresChatStore struct {
	q      *gen.Queries
	logger *logger.Logger
}

func NewChatStoreRepository(db interface{}, logger *logger.Logger) repositories.ChatStoreRepository {
	return &PostgresChatStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
	}
}
