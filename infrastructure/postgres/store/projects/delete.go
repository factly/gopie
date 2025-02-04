package projects

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Delete(ctx context.Context, id string) error {
	err := s.q.DeleteProject(ctx, id)
	if err != nil {
		s.logger.Error("Error deleting project", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}
