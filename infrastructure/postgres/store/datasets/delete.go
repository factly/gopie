package datasets

import "context"

func (s *PgDatasetStore) Delete(ctx context.Context, datasetID string) error {
	return s.q.DeleteDataset(ctx, datasetID)
}

func (s *PgDatasetStore) DeleteFailedUploadsByDatasetID(ctx context.Context, datasetID string) error {
	return s.q.DeleteFailedDatasetUpload(ctx, datasetID)
}
