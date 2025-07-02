package repositories

import "context"

type SourceRepository interface {
	// DownloadFile downloads a file from the source like s3, local file system, etc.
	DownloadFile(ctx context.Context, cfg map[string]any) (string, int64, error)
	// UploadFile uploads a file to the source like s3, local file system, etc.
	UploadFile(ctx context.Context, bucket, filePath string) (string, error)
}
