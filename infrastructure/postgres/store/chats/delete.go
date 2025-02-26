package chats

import (
	"context"

	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresChatStore) DeleteChat(ctx context.Context, id string) error {
	err := s.q.DeleteChat(ctx, pgtype.UUID{Bytes: uuid.MustParse(id), Valid: true})
	if err != nil {
		s.logger.Error("Error deleting chat", zap.Error(err))
		return err
	}

	return nil
}

func (s *PostgresChatStore) DeleteMessage(ctx context.Context, chatID string, messageID string) error {
	err := s.q.DeleteChatMessage(ctx, gen.DeleteChatMessageParams{
		ID:     pgtype.UUID{Bytes: uuid.MustParse(messageID), Valid: true},
		ChatID: pgtype.UUID{Bytes: uuid.MustParse(chatID), Valid: true},
	})
	if err != nil {
		s.logger.Error("Error deleting chat message", zap.Error(err))
		return err
	}

	return nil
}
