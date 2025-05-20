package repositories

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
)

type OlapRepository interface {
	Connect(*config.OlapDBConfig) error
	CreateTable(filePath, tableName, format string, alterColumnNames map[string]string) error
	CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string) error
	Query(query string) (*models.Result, error)
	DropTable(tableName string) error
	Close() error
	CreateTableFromPostgres(connectionString, sqlQuery, tableName string) error
	CreateTableFromMySql(connectionString, sqlQuery, tableName string) error
}
