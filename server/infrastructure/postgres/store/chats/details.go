package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PostgresChatStore) GetChatByID(ctx context.Context, chatID, userID string) (*models.Chat, error) {
	c, err := s.q.GetChatById(ctx, gen.GetChatByIdParams{
		ID:        pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
		CreatedBy: pgtype.Text{String: userID, Valid: true},
	})
	if err != nil {
		return nil, err
	}

	return &models.Chat{
		ID:        c.ID.String(),
		Title:     c.Title.String,
		CreatedAt: c.CreatedAt.Time,
		UpdatedAt: c.UpdatedAt.Time,
		CreatedBy: c.CreatedBy.String,
	}, nil
}
