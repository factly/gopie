package chats

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v5"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) UpdateChat(ctx context.Context, chatID string, params *models.UpdateChatParams) (*models.Chat, error) {
	c, err := s.q.UpdateChatTitle(ctx, gen.UpdateChatTitleParams{
		ID: pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
		Title: pgtype.Text{
			String: params.Title,
			Valid:  params.Title != "",
		},
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

func (s *PostgresChatStore) AddNewMessage(ctx context.Context, chatID string, messages []models.ChatMessage, keyStart int) ([]models.ChatMessage, error) {
	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		s.logger.Error("Error starting transaction", zap.Error(err))
		return nil, err
	}

	qtx := s.q.WithTx(tx)
	var chatMessages []models.ChatMessage

	for i, msg := range messages {
		msg.Key = keyStart + i
		choiceBytes, _ := json.Marshal(msg.Choices)
		chat, err := qtx.CreateChatMessage(ctx, gen.CreateChatMessageParams{
			ChatID:  pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
			Choices: choiceBytes,
			Object:  msg.Object,
			Model:   pgtype.Text{String: msg.Model, Valid: msg.Model != ""},
			Key:     int32(msg.Key),
		})
		if err != nil {
			s.logger.Error("Error creating chat message", zap.Error(err))
			return nil, err
		}

		choiceList := make([]models.Choice, 0)
		if len(msg.Choices) > 0 {
			_ = json.Unmarshal(choiceBytes, &choiceList)
		}

		chatMessage := models.ChatMessage{
			ID:        chat.ID.String(),
			CreatedAt: chat.CreatedAt.Time,
			Model:     chat.Model.String,
			Object:    chat.Object,
			Choices:   choiceList,
			Key:       int(msg.Key),
		}
		chatMessages = append(chatMessages, chatMessage)
	}

	if err := tx.Commit(ctx); err != nil {
		s.logger.Error("Error committing transaction", zap.Error(err))
		return nil, err
	}

	return chatMessages, nil
}
