package services

import (
	"context"
	"fmt"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
)

type Driver struct {
	olap   repositories.OlapRepository
	store  repositories.StoreRepository
	source repositories.SourceRepository
}

func NewDriver(olap repositories.OlapRepository, store repositories.StoreRepository, source repositories.SourceRepository) *Driver {
	return &Driver{
		olap:   olap,
		store:  store,
		source: source,
	}
}

func (d *Driver) UploadFile(ctx context.Context, filepath string) (*models.Dataset, error) {

	// parse filepath to bucketname and path
	// s3://bucketname/path/to/file
	bucket, path, err := parseFilepath(filepath)

	if err != nil {
		return nil, err
	}
	fmt.Println("==> ", bucket, path)

	filepath, err = d.source.DownloadFile(ctx, map[string]any{
		"bucket":   bucket,
		"filepath": path,
	})
	if err != nil {
		return nil, err
	}

	return &models.Dataset{Name: filepath}, nil
}

func parseFilepath(filepath string) (string, string, error) {
	// s3://bucketname/path/to/file
	// remove s3:// prefix if exists
	if len(filepath) > 5 && filepath[:5] == "s3://" {
		filepath = filepath[5:]
	}

	if filepath == "" {
		return "", "", fmt.Errorf("empty filepath provided")
	}

	// find the first slash after bucket name
	slashIndex := -1
	for i, char := range filepath {
		if char == '/' {
			slashIndex = i
			break
		}
	}

	if slashIndex == -1 {
		return "", "", fmt.Errorf("invalid filepath format: missing path separator '/'")
	}

	bucket := filepath[:slashIndex]
	if bucket == "" {
		return "", "", fmt.Errorf("empty bucket name")
	}

	path := filepath[slashIndex+1:]
	if path == "" {
		return "", "", fmt.Errorf("empty file path")
	}

	return bucket, path, nil
}
