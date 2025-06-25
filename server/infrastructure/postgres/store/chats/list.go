package chats

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PostgresChatStore) GetChatMessages(ctx context.Context, chatID string) ([]*models.ChatMessage, error) {
	msgs, err := s.q.GetChatMessages(ctx, chatID)
	if err != nil {
		return nil, err
	}

	chatMessages := make([]*models.ChatMessage, 0, len(msgs))

	for _, m := range msgs {
		choices := make([]models.Choice, 0)
		if m.Choices != nil {
			if err := json.Unmarshal(m.Choices, &choices); err != nil {
				return nil, err
			}
		}
		chatMessages = append(chatMessages, &models.ChatMessage{
			ID:        m.ID.String(),
			CreatedAt: m.CreatedAt.Time,
			Model:     m.Model.String,
			Object:    m.Object,
			Choices:   choices,
		})
	}

	return chatMessages, nil
}

func (s *PostgresChatStore) ListUserChats(ctx context.Context, userID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	res, err := s.q.ListChatsByUser(ctx, gen.ListChatsByUserParams{
		CreatedBy: pgtype.Text{String: userID, Valid: true},
		Offset:    int32(pagination.Offset),
		Limit:     int32(pagination.Limit),
	})
	if err != nil {
		return nil, err
	}

	chats := make([]*models.Chat, len(res))
	for _, c := range res {
		chats = append(chats, &models.Chat{
			ID:        c.ID,
			Title:     c.Title.String,
			CreatedAt: c.CreatedAt.Time,
			UpdatedAt: c.UpdatedAt.Time,
			CreatedBy: c.CreatedBy.String,
		})
	}
	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, len(res), chats)
	return &paginationView, nil
}
