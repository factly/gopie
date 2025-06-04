package chats

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) DeleteChat(ctx context.Context, id, createdBy string) error {
	err := s.q.DeleteChat(ctx, gen.DeleteChatParams{
		ID:        pgtype.UUID{Bytes: uuid.MustParse(id), Valid: true},
		CreatedBy: pgtype.Text{String: "system", Valid: true}, // Assuming system user for deletion
	})
	if err != nil {
		s.logger.Error("Error deleting chat", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}

	return nil
}
