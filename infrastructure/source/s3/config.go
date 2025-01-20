package s3

import (
	"fmt"
	"strings"

	"github.com/mitchellh/mapstructure"
)

type S3Config struct {
	AccessKeyID     string `mapstructure:"access_key_id"`
	SecretAccessKey string `mapstructure:"secret_access_key"`
	Region          string `mapstructure:"region"`
	Endpoint        string `mapstructure:"endpoint"`
}

type bucketURL struct {
	Scheme string
	Host   string
	Path   string
}

func ParseBucketURL(url string) (*bucketURL, error) {
	scheme, path, ok := strings.Cut(url, "://")
	if !ok {
		return nil, fmt.Errorf("invalid bucket URL: %s", url)
	}

	host, path, ok := strings.Cut(path, "/")
	if !ok {
		return nil, fmt.Errorf("invalid bucket URL: %s", url)
	}

	return &bucketURL{scheme, host, path}, nil
}

type s3SourceConfig struct {
	Path       string     `mapstructure:"path"`
	URL        string     `mapstructure:"url"`
	S3Endpoint string     `mapstructure:"s3_endpoint"`
	BucketURL  *bucketURL `mapstructure:"url"`
}

func parseS3SourceConfig(properties map[string]any) (*s3SourceConfig, error) {
	config := &s3SourceConfig{}
	if err := mapstructure.Decode(properties, config); err != nil {
		return nil, err
	}

	if config.URL != "" {
		bucketURL, err := ParseBucketURL(config.URL)
		if err != nil {
			return nil, err
		}
		config.BucketURL = bucketURL
	}

	return config, nil
}
