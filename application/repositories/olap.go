package repositories

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
)

type OlapRepository interface {
	Connect(*config.MotherDuckConfig) error
	CreateTable(filePath, tableName, format string) error
	CreateTableFromS3(s3Path, tableName, format string) error
	Query(query string) (*models.Result, error)
	DropTable(tableName string) error
	Close() error
}
