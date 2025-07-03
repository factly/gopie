package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
)

func (s *PostgresChatStore) GetChatByID(ctx context.Context, chatID string) (*models.Chat, error) {
	c, err := s.q.GetChatById(ctx, gen.GetChatByIdParams{
		ID: chatID,
	})
	if err != nil {
		return nil, err
	}

	return &models.Chat{
		ID:             c.ID,
		Title:          c.Title.String,
		CreatedAt:      c.CreatedAt.Time,
		UpdatedAt:      c.UpdatedAt.Time,
		CreatedBy:      c.CreatedBy.String,
		Visibility:     string(c.Visibility.ChatVisibility),
		OrganizationID: c.OrganizationID.String,
	}, nil
}
