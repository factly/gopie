package s3

import (
	"context"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"

	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg"
	domainCfg "github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/mitchellh/mapstructure"
	"go.uber.org/zap"
	"gocloud.dev/blob"
	"gocloud.dev/blob/s3blob"
)

// s3Source represents a connection to an AWS S3 storage bucket.
// It holds the configuration and logger required for S3 operations.
type s3Source struct {
	config *domainCfg.S3Config // AWS S3 configuration including credentials and endpoint
	logger *logger.Logger      // Logger instance for error and debug logging
}

func NewS3SourceRepository(config *domainCfg.S3Config, logger *logger.Logger) repositories.SourceRepository {
	return &s3Source{
		config: config,
		logger: logger,
	}
}

func (s *s3Source) getAWSConfig(ctx context.Context) (aws.Config, error) {
	// Validate s3 configuration exists
	if s.config == nil {
		return aws.Config{}, fmt.Errorf("s3 configuration is nil")
	}

	// Ensure region is specified
	if s.config.Region == "" {
		return aws.Config{}, fmt.Errorf("aws region is required")
	}

	// Load AWS configuration with custom credentials
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion(s.config.Region),
		config.WithCredentialsProvider(
			aws.CredentialsProviderFunc(func(ctx context.Context) (aws.Credentials, error) {
				// Validate required credentials
				if s.config.AccessKey == "" || s.config.SecretKey == "" {
					return aws.Credentials{}, fmt.Errorf("aws credentials are required")
				}
				// Return credentials object with access key, secret key
				return aws.Credentials{
					AccessKeyID:     s.config.AccessKey,
					SecretAccessKey: s.config.SecretKey,
				}, nil
			}),
		),
	)
	if err != nil {
		s.logger.Error("failed to load AWS config", zap.Error(err))
		return aws.Config{}, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return cfg, nil
}

func (c *s3Source) getS3Client(cfg aws.Config) (*s3.Client, error) {
	// Validate endpoint configuration
	if c.config == nil || c.config.Endpoint == "" {
		return nil, fmt.Errorf("s3 endpoint configuration is required")
	}

	// Create new S3 client with custom options
	return s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = true                          // Enable path-style addressing
		o.BaseEndpoint = aws.String(c.config.Endpoint) // Set custom endpoint
	}), nil
}

func (c *s3Source) openBucket(ctx context.Context, bucket string) (*blob.Bucket, error) {
	// Validate bucket name
	if bucket == "" {
		return nil, fmt.Errorf("bucket name is required")
	}

	// Get AWS configuration
	cfg, err := c.getAWSConfig(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get AWS config: %w", err)
	}

	// Create S3 client
	client, err := c.getS3Client(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create S3 client: %w", err)
	}

	// Open and return the bucket instance
	b, err := s3blob.OpenBucketV2(ctx, client, bucket, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to open bucket %s: %w", bucket, err)
	}

	return b, nil
}

type DownloadFileConfig struct {
	Bucket   string `mapstructure:"bucket"`
	FilePath string `mapstructure:"filepath"`
	Name     string `mapstructure:"name"`
}

// DownloadFile downloads a file from an S3 bucket to a local file.
// It returns the path to the downloaded file on success.
// Stores the file in /tmp directory with a unique name.
func (c *s3Source) DownloadFile(ctx context.Context, cfg map[string]any) (string, int64, error) {
	srcCfg := DownloadFileConfig{}
	err := mapstructure.Decode(cfg, &srcCfg)

	if srcCfg.FilePath == "" {
		return "", 0, fmt.Errorf("file path is required")
	}

	// extract file format from the file path
	// should consider the last part of the file path as the file name
	// after splitting the file path by '/'
	// e.g. file path: "path/to/file.txt"
	fileParts := strings.Split(srcCfg.FilePath, "/")
	fileName := fileParts[len(fileParts)-1]
	formatParts := strings.Split(fileName, ".")
	format := formatParts[len(formatParts)-1]

	c.logger.Info("starting file download from S3",
		zap.String("bucket", srcCfg.Bucket),
		zap.String("file", srcCfg.FilePath))

	buckObj, err := c.openBucket(ctx, srcCfg.Bucket)
	if err != nil {
		c.logger.Error("failed to open bucket",
			zap.String("bucket", srcCfg.Bucket),
			zap.Error(err))
		return "", 0, fmt.Errorf("failed to open bucket: %w", err)
	}

	c.logger.Debug("bucket opened successfully", zap.String("bucket", srcCfg.Bucket))

	obj, err := buckObj.NewReader(ctx, srcCfg.FilePath, nil)
	if err != nil {
		c.logger.Error("failed to open file",
			zap.String("bucket", srcCfg.Bucket),
			zap.String("file", srcCfg.FilePath),
			zap.Error(err))
		return "", 0, fmt.Errorf("failed to open file: %w", err)
	}

	c.logger.Debug("file opened successfully",
		zap.String("bucket", srcCfg.Bucket),
		zap.String("file", srcCfg.FilePath))

	defer obj.Close()

	tableName := srcCfg.Name
	if tableName == "" {
		tableName = fmt.Sprintf("gp_%s", pkg.RandomString(13))
	}

	// Extract the filename from the path for the local file
	fileName = fmt.Sprintf("/tmp/%s.%s",
		tableName,
		format,
	)

	file, err := os.Create(fileName)
	if err != nil {
		c.logger.Error("failed to create file",
			zap.String("path", fileName),
			zap.Error(err))
		return "", 0, fmt.Errorf("failed to create file: %w", err)
	}
	defer file.Close()

	written, err := io.Copy(file, obj)
	if err != nil {
		c.logger.Error("failed to write file contents",
			zap.String("bucket", srcCfg.Bucket),
			zap.String("file", srcCfg.FilePath),
			zap.Error(err))
		return "", 0, fmt.Errorf("failed to write file: %w", err)
	}

	c.logger.Info("file downloaded successfully",
		zap.String("bucket", srcCfg.Bucket),
		zap.String("file", srcCfg.FilePath),
		zap.String("saved_to", fileName),
		zap.Int64("bytes_downloaded", written))

	return fileName, written, nil
}

func (c *s3Source) UploadFile(ctx context.Context, bucket, filePath string) (string, error) {
	if bucket == "" || filePath == "" {
		return "", fmt.Errorf("bucket and file path are required")
	}

	c.logger.Info("starting file upload to S3",
		zap.String("bucket", bucket),
		zap.String("file", filePath))

	buckObj, err := c.openBucket(ctx, bucket)
	if err != nil {
		c.logger.Error("failed to open bucket",
			zap.String("bucket", bucket),
			zap.Error(err))
		return "", fmt.Errorf("failed to open bucket: %w", err)
	}

	file, err := os.Open(filePath)
	if err != nil {
		c.logger.Error("failed to open file",
			zap.String("file", filePath),
			zap.Error(err))
		return "", fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	// Read the file content
	fileContent, err := io.ReadAll(file)
	if err != nil {
		c.logger.Error("failed to read file content",
			zap.String("file", filePath),
			zap.Error(err))
		return "", fmt.Errorf("failed to read file content: %w", err)
	}

	// Get the filename from the path for S3
	filePathParts := strings.Split(filePath, "/")
	fileName := filePathParts[len(filePathParts)-1]

	// Upload the file content as bytes
	err = buckObj.WriteAll(ctx, fileName, fileContent, nil)
	if err != nil {
		c.logger.Error("failed to upload file",
			zap.String("bucket", bucket),
			zap.String("file", fileName),
			zap.Error(err))
		return "", fmt.Errorf("failed to upload file: %w", err)
	}

	c.logger.Info("file uploaded successfully",
		zap.String("bucket", bucket),
		zap.String("file", fileName),
		zap.Int("bytes_uploaded", len(fileContent)))

	return fileName, nil
}
