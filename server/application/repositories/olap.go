package repositories

import (
	"context"
	"io"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
)

type QueryTransformer func(query string, db any) (string, error)

type OlapRepository interface {
	Connect(*config.OlapDBConfig) error
	GetDB() any
	GetHelperDB() any
	CreateTable(filePath, tableName, format string, alterColumnNames map[string]string, ignoreError bool) error
	CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string, ignoreError bool) error
	Query(query string, transformers ...QueryTransformer) (*models.Result, error)
	DropTable(tableName string) error
	Close() error
	CreateTableFromPostgres(connectionString, sqlQuery, tableName string) error
	CreateTableFromMySql(connectionString, sqlQuery, tableName string) error
	ExecuteQueryAndStreamCSV(ctx context.Context, sql string, writer io.Writer) error
}
