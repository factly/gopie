package chats

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) DetailsChat(ctx context.Context, id string) (*models.Chat, error) {
	c, err := s.q.GetChat(ctx, pgtype.UUID{Bytes: uuid.MustParse(id), Valid: true})
	if err != nil {
		s.logger.Error("Error fetching chat", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}

	return &models.Chat{
		ID:        c.ID.String(),
		Name:      c.Name,
		CreatedAt: c.CreatedAt.Time,
		UpdatedAt: c.UpdatedAt.Time,
		CreatedBy: c.CreatedBy.String,
	}, nil
}
