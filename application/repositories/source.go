package repositories

import "context"

type SourceRepository interface {
	// DownloadFile downloads a file from the source like s3, local file system, etc.
	DownloadFile(ctx context.Context, cfg map[string]any) (string, error)
}
