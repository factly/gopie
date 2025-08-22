package s3

import (
	"context"
	"io"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/feature/s3/manager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/factly/gopie/application/repositories"
	appConfig "github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

// S3ObjectStore provides methods to interact with an S3-compatible object store.
type S3ObjectStore struct {
	config        appConfig.S3Config
	logger        *logger.Logger
	client        *s3.Client
	bucket        string
	presignClient *s3.PresignClient
	uploader      *manager.Uploader
}

// NewS3ObjectStore creates a new, uninitialized instance of S3ObjectStore.
func NewS3ObjectStore(config appConfig.S3Config, bucket string, logger *logger.Logger) repositories.S3SourceRepository {
	return &S3ObjectStore{
		config: config,
		logger: logger,
		bucket: bucket,
	}
}

// Connect initializes the S3 client using a stable endpoint resolution method.
func (s *S3ObjectStore) Connect(ctx context.Context) error {
	s.logger.Info("Connecting to S3 object store", zap.String("endpoint", s.config.Endpoint), zap.String("region", s.config.Region))

	// This resolver function is a stable way to handle custom endpoints,
	// avoiding the dependency issues with the newer V2 resolver interface.
	resolver := aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...any) (aws.Endpoint, error) {
		return aws.Endpoint{
			URL:               s.config.Endpoint,
			SigningRegion:     s.config.Region,
			HostnameImmutable: true, // Important for S3-compatible services like Minio
		}, nil
	})

	// Load the base configuration, providing static credentials and our custom endpoint resolver.
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion(s.config.Region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(s.config.AccessKey, s.config.SecretKey, "")),
		config.WithEndpointResolverWithOptions(resolver),
	)
	if err != nil {
		s.logger.Error("Failed to load S3 configuration", zap.Error(err))
		return err
	}

	// Create the S3 client from the configuration, adding the option for path-style addressing.
	s.client = s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = true
	})

	// Initialize the uploader and presign client using the configured S3 client.
	s.uploader = manager.NewUploader(s.client)
	s.presignClient = s3.NewPresignClient(s.client)

	s.logger.Info("Successfully connected to S3 object store")
	return nil
}

// UploadFile now uses the multipart uploader for robust, non-seekable stream uploads.
func (s *S3ObjectStore) UploadFile(ctx context.Context, key string, body io.Reader) (*manager.UploadOutput, error) {
	s.logger.Info("Starting file upload to S3", zap.String("bucket", s.bucket), zap.String("key", key))

	// The uploader handles the non-seekable stream gracefully, uploading it in chunks.
	output, err := s.uploader.Upload(ctx, &s3.PutObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
		Body:   body,
	})
	if err != nil {
		s.logger.Error("Failed to upload file to S3", zap.String("bucket", s.bucket), zap.String("key", key), zap.Error(err))
		return nil, err
	}

	s.logger.Info("Successfully uploaded file to S3", zap.String("bucket", s.bucket), zap.String("key", key), zap.String("upload_id", output.UploadID))
	return output, nil
}

// GetPresignedURL generates a temporary, pre-signed URL that grants access to an S3 object for a limited time.
func (s *S3ObjectStore) GetPresignedURL(ctx context.Context, key string, lifetime time.Duration) (string, error) {
	s.logger.Info("Generating pre-signed URL", zap.String("bucket", s.bucket), zap.String("key", key))

	request, err := s.presignClient.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
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
