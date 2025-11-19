package repositories

import (
	"context"
	"database/sql"
	"time"

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
	CreateTableFromS3WithTx(tx *sql.Tx, s3Path, tableName, format string, alterColumnNames map[string]string, ignoreError bool) error
	Query(query string, transformers ...QueryTransformer) (*models.Result, error)
	DropTable(tableName string) error
	DropTableWithTx(tx *sql.Tx, tableName string) error
	FullTableRefreshPostgres(connectionString, sqlQuery, tableName string) error
	FullTableRefreshMySQL(connectionString, sqlQuery, tableName string) error
	IncrementalRefreshPostgres(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error
	IncrementalRefreshMySQL(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error
	GetLatestTimestamp(tableName, timestampColumn string) (*string, error)
	Close() error
	CreateTableFromPostgres(connectionString, sqlQuery, tableName string) error
	CreateTableFromMySql(connectionString, sqlQuery, tableName string) error
	ExecuteQueryAndStoreInS3(ctx context.Context, sql, format, outputPath string) error
	TableNames(sql string) ([]string, error)
}
