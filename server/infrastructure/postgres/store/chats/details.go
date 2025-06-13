package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PostgresChatStore) GetChatByID(ctx context.Context, chatID, userID string) (*models.Chat, error) {
	c, err := s.q.GetChatById(ctx, gen.GetChatByIdParams{
		ID:        chatID,
		CreatedBy: pgtype.Text{String: userID, Valid: true},
	})
	if err != nil {
		return nil, err
	}

	return &models.Chat{
		ID:        c.ID,
		Title:     c.Title.String,
		CreatedAt: c.CreatedAt.Time,
		UpdatedAt: c.UpdatedAt.Time,
		CreatedBy: c.CreatedBy.String,
	}, nil
}
