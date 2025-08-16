package repositories

import (
	"context"
	"io"
	"time"

	"github.com/aws/aws-sdk-go-v2/feature/s3/manager"
)

type S3SourceRepository interface {
	Connect(ctx context.Context) error
	UploadFile(ctx context.Context, key string, body io.Reader) (*manager.UploadOutput, error)
	GetPresignedURL(ctx context.Context, key string, lifetime time.Duration) (string, error)
}
