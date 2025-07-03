package chats

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v5"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) UpdateChat(ctx context.Context, chatID string, params *models.UpdateChatParams) (*models.Chat, error) {
	c, err := s.q.UpdateChatTitle(ctx, gen.UpdateChatTitleParams{
		ID: chatID,
		Title: pgtype.Text{
			String: params.Title,
			Valid:  params.Title != "",
		},
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

func (s *PostgresChatStore) UpdateChatVisibility(ctx context.Context, chatID, userID string, params *models.UpdateChatVisibilityParams) (*models.Chat, error) {
	visibility := gen.NullChatVisibility{
		ChatVisibility: gen.ChatVisibility(params.Visibility),
		Valid:          params.Visibility != "",
	}

	c, err := s.q.UpdateChatVisibility(ctx, gen.UpdateChatVisibilityParams{
		ID:         chatID,
		Visibility: visibility,
		CreatedBy: pgtype.Text{
			String: userID,
			Valid:  userID != "",
		},
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

func (s *PostgresChatStore) AddNewMessage(ctx context.Context, chatID string, messages []models.ChatMessage) ([]models.ChatMessage, error) {
	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		s.logger.Error("Error starting transaction", zap.Error(err))
		return nil, err
	}

	qtx := s.q.WithTx(tx)
	var chatMessages []models.ChatMessage

	for _, msg := range messages {
		choiceBytes, _ := json.Marshal(msg.Choices)
		chat, err := qtx.CreateChatMessage(ctx, gen.CreateChatMessageParams{
			ChatID:  chatID,
			Choices: choiceBytes,
			Object:  msg.Object,
			Model:   pgtype.Text{String: msg.Model, Valid: msg.Model != ""},
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
		}
		chatMessages = append(chatMessages, chatMessage)
	}

	if err := tx.Commit(ctx); err != nil {
		s.logger.Error("Error committing transaction", zap.Error(err))
		return nil, err
	}

	return chatMessages, nil
}
