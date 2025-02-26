package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PostgresChatStore) UpdateChat(ctx context.Context, chatID string, params *models.UpdateChatParams) (*models.Chat, error) {
	c, err := s.q.UpdateChat(ctx, gen.UpdateChatParams{
		ID:   pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
		Name: params.Name,
	})
	if err != nil {
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

func (s *PostgresChatStore) AddNewMessage(ctx context.Context, chatID string, message models.ChatMessage) (*models.ChatMessage, error) {
	m, err := s.q.CreateChatMessage(ctx, gen.CreateChatMessageParams{
		ChatID:  pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
		Content: message.Content,
		Role:    message.Role,
	})
	if err != nil {
		return nil, err
	}
	return &models.ChatMessage{
		ID:        m.ID.String(),
		Content:   m.Content,
		Role:      m.Role,
		CreatedAt: m.CreatedAt.Time,
	}, nil
}
