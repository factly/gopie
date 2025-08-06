package s3

import (
	"context"
	"io"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	appConfig "github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"go.uber.org/zap"
)

// S3ObjectStore provides methods to interact with an S3-compatible object store.
type S3ObjectStore struct {
	config        appConfig.S3Config
	logger        *logger.Logger
	client        *s3.Client
	presignClient *s3.PresignClient
}

// NewS3ObjectStore creates a new, uninitialized instance of S3ObjectStore.
func NewS3ObjectStore(config appConfig.S3Config, logger *logger.Logger) *S3ObjectStore {
	return &S3ObjectStore{
		config: config,
		logger: logger,
	}
}

// customEndpointResolver is a simple struct that implements the s3.EndpointResolverV2 interface.
// It's used to direct the S3 client to a custom endpoint, like Minio, which is required by the modern AWS SDK.
type customEndpointResolver struct {
	URL string
}

func (s *S3ObjectStore) Connect(ctx context.Context) error {
	s.logger.Info("Connecting to S3 object store", zap.String("endpoint", s.config.Endpoint), zap.String("region", s.config.Region))

	// Load the base configuration, providing static credentials.
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion(s.config.Region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(s.config.AccessKey, s.config.SecretKey, "")),
	)
	if err != nil {
		s.logger.Error("Failed to load S3 configuration", zap.Error(err))
		return err
	}

	s.client = s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = true
	})

	s.presignClient = s3.NewPresignClient(s.client)

	s.logger.Info("Successfully connected to S3 object store")
	return nil
}

type ProgressCallback func(bytesRead, totalSize int64)

type ProgressTrackingReader struct {
	reader     io.Reader
	totalSize  int64
	bytesRead  int64
	onProgress ProgressCallback
}

func (r *ProgressTrackingReader) Read(p []byte) (n int, err error) {
	n, err = r.reader.Read(p)
	if n > 0 {
		r.bytesRead += int64(n)
		if r.onProgress != nil {
			r.onProgress(r.bytesRead, r.totalSize)
		}
	}
	return n, err
}

// UploadFile streams the content from an io.Reader to the specified S3 bucket and object key,
func (s *S3ObjectStore) UploadFile(ctx context.Context, key string, body io.Reader, totalSize int64, progressCb ProgressCallback) (*s3.PutObjectOutput, error) {
	s.logger.Info("Starting file upload to S3", zap.String("bucket", s.config.Bucket), zap.String("key", key), zap.Int64("size", totalSize))

	progressReader := &ProgressTrackingReader{
		reader:     body,
		totalSize:  totalSize,
		onProgress: progressCb,
	}

	output, err := s.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:        aws.String(s.config.Bucket),
		Key:           aws.String(key),
		Body:          progressReader,
		ContentLength: &totalSize,
	})
	if err != nil {
		s.logger.Error("Failed to upload file to S3", zap.String("bucket", s.config.Bucket), zap.String("key", key), zap.Error(err))
		return nil, err
	}

	s.logger.Info("Successfully uploaded file to S3", zap.String("bucket", s.config.Bucket), zap.String("key", key))
	return output, nil
}

// GetPresignedURL generates a temporary, pre-signed URL that grants access to an S3 object for a limited time.
func (s *S3ObjectStore) GetPresignedURL(ctx context.Context, key string, lifetime time.Duration) (string, error) {
	s.logger.Info("Generating pre-signed URL", zap.String("bucket", s.config.Bucket), zap.String("key", key))

	request, err := s.presignClient.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.config.Bucket),
		Key:    aws.String(key),
	}, func(opts *s3.PresignOptions) {
		opts.Expires = lifetime
	})
	if err != nil {
		s.logger.Error("Failed to generate pre-signed URL", zap.String("key", key), zap.Error(err))
		return "", err
	}

	s.logger.Info("Successfully generated pre-signed URL", zap.String("key", key))
	return request.URL, nil
}
