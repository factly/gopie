package chats

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) CreateChat(ctx context.Context, params *models.CreateChatParams) (*models.ChatWithMessages, error) {
	// Create a new chat
	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		s.logger.Error("Error starting transaction", zap.Error(err))
		return nil, err
	}
	defer func() {
		if err != nil {
			tx.Rollback(ctx)
		}
	}()

	qtx := s.q.WithTx(tx)

	c, err := qtx.CreateChat(ctx, gen.CreateChatParams{
		Title:     pgtype.Text{String: params.Title, Valid: true},
		CreatedBy: pgtype.Text{String: params.CreatedBy, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error creating chat", zap.Error(err))
		return nil, err
	}

	messages := make([]models.ChatMessage, 0, len(params.Messages))

	// Process messages sequentially within the transaction
	for _, message := range params.Messages {
		choiceBytes, _ := json.Marshal(message.Choices)
		// Create chat message in DB
		chat, err := qtx.CreateChatMessage(ctx, gen.CreateChatMessageParams{
			ChatID:  c.ID,
			Choices: choiceBytes,
			Object:  message.Object,
			Model:   pgtype.Text{String: message.Model, Valid: message.Model != ""},
			Key:     int32(message.Key),
		})
		if err != nil {
			s.logger.Error("Error creating chat message", zap.Error(err))
			return nil, err
		}

		choiceList := make([]models.Choice, 0)
		if len(message.Choices) > 0 {
			_ = json.Unmarshal(choiceBytes, &choiceList)
		}

		// Map DB result to domain model
		chatMessage := models.ChatMessage{
			ID:        chat.ID.String(),
			CreatedAt: chat.CreatedAt.Time,
			Model:     chat.Model.String,
			Object:    chat.Object,
			Choices:   choiceList,
			Key:       int(message.Key),
		}

		messages = append(messages, chatMessage)
	}

	// Commit transaction after all messages have been added
	err = tx.Commit(ctx)
	if err != nil {
		s.logger.Error("Error committing transaction", zap.Error(err))
		return nil, err
	}

	return &models.ChatWithMessages{
		ID:        c.ID.String(),
		Title:     c.Title.String,
		CreatedAt: c.CreatedAt.Time,
		UpdatedAt: c.UpdatedAt.Time,
		CreatedBy: c.CreatedBy.String,
		Messages:  messages,
	}, nil
}
