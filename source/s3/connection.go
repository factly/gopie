package s3

import (
	"context"
	"errors"
	"fmt"
	"math"
	"net/http"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/c2h5oh/datasize"
	"github.com/factly/gopie/pkg"
	"github.com/factly/gopie/source"
	"gocloud.dev/blob"
	"gocloud.dev/blob/s3blob"
)

type Connection struct {
	config *configProperties
	logger *pkg.Logger
}

func (c *Connection) getCredentials() (*credentials.Credentials, error) {
	staticProvider := &credentials.StaticProvider{}
	staticProvider.AccessKeyID = c.config.AccessKeyID
	staticProvider.SecretAccessKey = c.config.SecretAccessKey
	staticProvider.SessionToken = c.config.SessionToken
	staticProvider.ProviderName = credentials.StaticProviderName

	creds := credentials.NewCredentials(staticProvider)

	if _, err := creds.Get(); err != nil {
		return nil, err
	}

	return creds, nil
}

func (c *Connection) DownloadFiles(ctx context.Context, src map[string]any, bucket string) (source.FileIterator, error) {
	conf, err := parseSourceProperties(src)

	if err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	creds, err := c.getCredentials()
	if err != nil {
		return nil, err
	}

	buckObj, err := c.openBucket(ctx, bucket, creds)
	if err != nil {
		return nil, fmt.Errorf("failed to open bucket %q, %w", conf.url.Host, err)
	}

	var batchSize datasize.ByteSize
	if conf.BatchSize == "-1" {
		batchSize = math.MaxInt64
	}
	opts := source.BlobOptions{
		GlobPattern:           "**/*.{csv,parquet}",
		RetainFiles:           c.config.RetainFiles,
		BatchSizeBytes:        int64(batchSize.Bytes()),
		GlobPageSize:          conf.GlobPageSize,
		GlobMaxTotalSize:      conf.GlobMaxTotalSize,
		GlobMaxObjectsMatched: conf.GlobMaxObjectMatched,
		GlobMaxObjectsListed:  conf.GlobMaxObjetsListed,
		KeepFilesUntilClose:   conf.BatchSize == "-1",
	}

	path := src["path"].(string)

	it, err := source.NewIterator(ctx, buckObj, opts, *c.logger, &path)
	if err != nil {
		var failureErr awserr.RequestFailure
		if !errors.As(err, &failureErr) {
			return nil, err
		}

		if (failureErr.StatusCode() == http.StatusForbidden || failureErr.StatusCode() == http.StatusBadRequest) && creds != credentials.AnonymousCredentials {
			c.logger.Error("s3 list objects failed")
			return nil, fmt.Errorf("failed to open bucket %q, %w", conf.url, err)
		}
	}

	return it, nil
}

func (c *Connection) getAwsSessionConfig(creds *credentials.Credentials) (*session.Session, error) {
	endpoint := c.config.Endpoint
	return session.NewSession(&aws.Config{
		Region:           aws.String(c.config.Region),
		Endpoint:         &endpoint,
		S3ForcePathStyle: aws.Bool(true),
		Credentials:      creds,
	})
}

func (c *Connection) openBucket(ctx context.Context, bucket string, creds *credentials.Credentials) (*blob.Bucket, error) {
	sess, err := c.getAwsSessionConfig(creds)

	if err != nil {
		return nil, fmt.Errorf("failed to start session: %w", err)
	}

	return s3blob.OpenBucket(ctx, sess, bucket, nil)
}
