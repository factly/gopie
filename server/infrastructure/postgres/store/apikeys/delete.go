package apikeys

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) Delete(ctx context.Context, id string) error {
	uid, err := uuid.Parse(id)
	if err != nil {
		return err
	}

	err = s.q.DeleteAPIKey(ctx, pgtype.UUID{Bytes: uid, Valid: true})
	if err != nil {
		s.logger.Error("Error deleting API key", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}
