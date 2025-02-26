package chats

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) CreateChat(ctx context.Context, params *models.CreateChatParams) (*models.ChatWithMessages, error) {
	//INFO: ignoring error because validator will catch it
	parseUUID, _ := uuid.Parse(params.DatasetID)
	c, err := s.q.CreateChat(ctx, gen.CreateChatParams{
		Name:      params.Name,
		DatasetID: pgtype.UUID{Bytes: parseUUID, Valid: true},
		CreatedBy: pgtype.Text{String: params.CreatedBy, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error creating chat", zap.Error(err))
		return nil, err
	}

	errChan := make(chan error)
	chatsChan := make(chan *models.ChatMessage, len(params.Messages))
	for _, message := range params.Messages {
		go func(msg models.ChatMessage) {
			chat, err := s.q.CreateChatMessage(ctx, gen.CreateChatMessageParams{
				ChatID:    c.ID,
				Content:   msg.Content,
				Role:      msg.Role,
				CreatedAt: pgtype.Timestamptz{Valid: true, Time: msg.CreatedAt},
			})
			errChan <- err
			chatsChan <- &models.ChatMessage{
				ID:        chat.ID.String(),
				Content:   chat.Content,
				Role:      chat.Role,
				CreatedAt: chat.CreatedAt.Time,
			}
		}(message)
	}

	for range params.Messages {
		if err := <-errChan; err != nil {
			s.logger.Error("Error creating chat message", zap.Error(err))
			return nil, err
		}
	}

	var messages []models.ChatMessage
	for range params.Messages {
		messages = append(messages, *<-chatsChan)
	}

	return &models.ChatWithMessages{
		ID:        c.ID.String(),
		Name:      c.Name,
		CreatedAt: c.CreatedAt.Time,
		UpdatedAt: c.UpdatedAt.Time,
		CreatedBy: c.CreatedBy.String,
		Messages:  messages,
	}, nil
}
