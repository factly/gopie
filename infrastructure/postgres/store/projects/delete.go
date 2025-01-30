package projects

import (
	"context"

	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Delete(ctx context.Context, id string) error {
	err := s.q.DeleteProject(ctx, id)
	if err != nil {
		s.logger.Error("Error deleting project", zap.Error(err))
		return err
	}
	return nil
}
