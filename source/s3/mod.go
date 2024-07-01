package s3

import (
	"github.com/factly/gopie/pkg"
	"github.com/factly/gopie/source"
	"github.com/mitchellh/mapstructure"
)

func NewS3Objectstore(logger *pkg.Logger, conf map[string]any) source.ObjectStore {
	var config *configProperties
	err := mapstructure.WeakDecode(conf, &config)
	if err != nil {
		logger.Fatal(err.Error())
		return nil
	}
	return &Connection{config, logger}
}
