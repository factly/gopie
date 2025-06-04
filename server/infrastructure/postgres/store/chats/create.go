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

	qtx := s.q.WithTx(tx)

	c, err := qtx.CreateChat(ctx, gen.CreateChatParams{
		Title:     pgtype.Text{String: params.Title, Valid: true},
		CreatedBy: pgtype.Text{String: params.CreatedBy, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error creating chat", zap.Error(err))
		tx.Rollback(ctx)
		return nil, err
	}

	errChan := make(chan error)
	chatsChan := make(chan models.ChatMessage, len(params.Messages))

	for _, message := range params.Messages {
		go func(msg models.ChatMessage) {
			choiceBytes, _ := json.Marshal(msg.Choices)
			// Create chat message in DB
			chat, err := s.q.CreateChatMessage(ctx, gen.CreateChatMessageParams{
				ChatID:  c.ID,
				Choices: choiceBytes,
				Object:  msg.Object,
				Model:   pgtype.Text{String: msg.Model, Valid: msg.Model != ""},
			})
			if err != nil {
				errChan <- err
				tx.Rollback(ctx)
				return
			}

			choiceList := make([]models.Choice, 0)
			if len(msg.Choices) > 0 {
				_ = json.Unmarshal(choiceBytes, &choiceList)
			}

			// Map DB result to domain model
			chatMessage := models.ChatMessage{
				ID:        chat.ID.String(),
				CreatedAt: chat.CreatedAt.Time,
				Model:     chat.Model.String,
				Object:    chat.Object,
				Choices:   choiceList,
			}

			chatsChan <- chatMessage
			errChan <- nil
		}(message)
	}

	err = tx.Commit(ctx)
	if err != nil {
		s.logger.Error("Error committing transaction", zap.Error(err))
		return nil, err
	}
	// Wait for all goroutines to complete
	var messages []models.ChatMessage
	for range params.Messages {
		err := <-errChan
		if err != nil {
			return nil, err
		}
		messages = append(messages, <-chatsChan)
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
