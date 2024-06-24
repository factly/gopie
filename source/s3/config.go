package s3

import (
	"fmt"

	"github.com/bmatcuk/doublestar/v4"
	"github.com/factly/gopie/pkg"
	"github.com/mitchellh/mapstructure"
)

type configProperties struct {
	AccessKeyID     string `mapstructure:"aws_access_key_id"`
	SecretAccessKey string `mapstructure:"aws_secret_access_key"`
	SessionToken    string `mapstructure:"aws_access_token"`
	AllowHostAccess bool   `mapstructure:"allow_host_access"`
	RetainFiles     bool   `mapstructure:"retain_files"`
}

type sourceProperties struct {
	Path                 string         `mapstructure:"path"`
	URI                  string         `mapstructure:"uri"`
	AWSRegion            string         `mapstructure:"aws_region"`
	GlobMaxTotalSize     int64          `mapstructure:"glob.max_total_size"`
	GlobMaxObjectMatched int            `mapstructure:"glob.max_object_matched"`
	GlobMaxObjetsListed  int64          `mapstructure:"glob.max_objets_listed"`
	GlobPageSize         int            `mapstructure:"glob.page_size"`
	S3Endpoint           string         `mapstructure:"s3_endpoint"`
	Extract              map[string]any `mapstructure:"extract"`
	BatchSize            string         `mapstructure:"batch_size"`
	url                  *pkg.URL       `mapstructure:"url"`
	// extractPolicy        any            `mapstructure:"extract_policy"`
}

func parseSourceProperties(props map[string]any) (*sourceProperties, error) {
	conf := &sourceProperties{}
	err := mapstructure.WeakDecode(props, conf)
	if err != nil {
		return nil, err
	}

	if conf.URI != "" {
		conf.Path = conf.URI
	}

	if !doublestar.ValidatePattern(conf.Path) {
		return nil, fmt.Errorf("glob pattern is %s invalid", conf.Path)
	}

	return conf, nil
}
