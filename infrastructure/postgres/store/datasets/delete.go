package datasets

import "context"

func (s *PostgresDatasetStore) Delete(ctx context.Context, datasetID string) error {
	return s.q.DeleteDataset(ctx, datasetID)
}
