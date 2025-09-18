package apikeys

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) Delete(ctx context.Context, id, orgID string) error {
	uid, err := uuid.Parse(id)
	if err != nil {
		return err
	}

	err = s.q.DeleteAPIKey(ctx, gen.DeleteAPIKeyParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	})
	if err != nil {
		s.logger.Error("Error deleting API key", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}

