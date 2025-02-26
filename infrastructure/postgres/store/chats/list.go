package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PostgresChatStore) GetChatMessages(ctx context.Context, chatID string, pagination models.Pagination) (*models.PaginationView[*models.ChatMessage], error) {
	cID := uuid.MustParse(chatID)
	count, err := s.q.GetChatMessagesCount(ctx, pgtype.UUID{Bytes: cID, Valid: true})
	if err != nil {
		return nil, err
	}
	messages, err := s.q.ListChatMessages(ctx, gen.ListChatMessagesParams{
		ChatID: pgtype.UUID{Bytes: cID, Valid: true},
		Limit:  int32(pagination.Limit),
		Offset: int32(pagination.Offset),
	})

	if err != nil {
		return nil, err
	}

	chatMessages := make([]*models.ChatMessage, 0, len(messages))

	for _, m := range messages {
		chatMessages = append(chatMessages, &models.ChatMessage{
			ID:        m.ID.String(),
			Content:   m.Content,
			Role:      m.Role,
			CreatedAt: m.CreatedAt.Time,
		})
	}

	paginatedMessages := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), chatMessages)
	return &paginatedMessages, nil
}

func (s *PostgresChatStore) ListUserChats(ctx context.Context, userID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	res, err := s.q.ListUserChats(ctx, gen.ListUserChatsParams{
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
			ID:        c.ID.String(),
			Name:      c.Name,
			CreatedAt: c.CreatedAt.Time,
			UpdatedAt: c.UpdatedAt.Time,
			CreatedBy: c.CreatedBy.String,
		})
	}
	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, len(res), chats)
	return &paginationView, nil
}

func (s *PostgresChatStore) GetChatsByDatasetID(ctx context.Context, datasetID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	count, err := s.q.GetDatasetChatsCount(ctx, pgtype.UUID{Bytes: uuid.MustParse(datasetID), Valid: true})
	if err != nil {
		return nil, err
	}
	res, err := s.q.ListDatasetChats(ctx, gen.ListDatasetChatsParams{
		DatasetID: pgtype.UUID{Bytes: uuid.MustParse(datasetID), Valid: true},
		Limit:     int32(pagination.Limit),
		Offset:    int32(pagination.Offset),
	})
	if err != nil {
		return nil, err
	}

	chats := make([]*models.Chat, 0, len(res))
	for _, c := range res {
		chats = append(chats, &models.Chat{
			ID:        c.ID.String(),
			Name:      c.Name,
			CreatedAt: c.CreatedAt.Time,
			UpdatedAt: c.UpdatedAt.Time,
			CreatedBy: c.CreatedBy.String,
		})
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), chats)
	return &paginationView, nil
}
