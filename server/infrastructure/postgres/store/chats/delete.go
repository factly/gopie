package chats

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) DeleteChat(ctx context.Context, id, createdBy, orgID string) error {
	err := s.q.DeleteChat(ctx, gen.DeleteChatParams{
		ID:             id,
		CreatedBy:      pgtype.Text{String: createdBy, Valid: true},
		OrganizationID: pgtype.Text{String: orgID, Valid: true},
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
