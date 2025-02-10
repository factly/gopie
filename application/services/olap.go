package services

import (
	"context"
	"fmt"
	"strings"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

type OlapService struct {
	olap   repositories.OlapRepository
	source repositories.SourceRepository
	logger *logger.Logger
}

func NewOlapService(olap repositories.OlapRepository, source repositories.SourceRepository, logger *logger.Logger) *OlapService {
	return &OlapService{
		olap:   olap,
		source: source,
		logger: logger,
	}
}

func (d *OlapService) IngestS3File(ctx context.Context, s3Path string, name string) (*models.UploadDatasetResult, error) {
	tableName := name
	if tableName == "" {
		tableName = fmt.Sprintf("gp_%s", pkg.RandomString(13))
	}
	// extract file format and table name from s3Path
	parts := strings.Split(s3Path, "/")
	formatParts := strings.Split(parts[len(parts)-1], ".")
	format := formatParts[len(formatParts)-1]
	err := d.olap.CreateTableFromS3(s3Path, tableName, format)
	return &models.UploadDatasetResult{
		FilePath:  s3Path,
		Format:    format,
		Size:      0,
		TableName: tableName,
	}, err
}

func (d *OlapService) IngestFile(ctx context.Context, filepath string, name string) (*models.UploadDatasetResult, error) {
	// parse filepath to bucketname and path
	// s3://bucketname/path/to/file
	bucket, path, err := parseFilepath(filepath)

	if err != nil {
		return nil, err
	}

	filepath, size, err := d.source.DownloadFile(ctx, map[string]any{
		"bucket":   bucket,
		"filepath": path,
		"name":     name,
	})
	if err != nil {
		return nil, err
	}

	// extract file format and table name from filepath
	pathParts := strings.Split(filepath, "/")
	filenameParts := strings.Split(pathParts[2], ".")

	tableName := filenameParts[0]
	format := filenameParts[1]
	res := models.UploadDatasetResult{
		FilePath:  filepath,
		TableName: tableName,
		Format:    format,
		Size:      int(size),
	}

	err = d.olap.CreateTable(filepath, tableName, format)
	if err != nil {
		return &res, err
	}

	return &res, nil
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

func (d *OlapService) SqlQuery(sql string) (map[string]any, error) {

	hasMultiple, err := pkg.HasMultipleStatements(sql)
	if err != nil {
		d.logger.Error("Invalid query: %v", zap.Error(err))
		return nil, err
	}

	if hasMultiple {
		d.logger.Error("Multiple statements are not allowed", zap.String("query", sql))
		return nil, domain.ErrMultipleSqlStatements
	}

	isSelect, err := pkg.IsSelectStatement(sql)
	if err != nil {
		d.logger.Error("Invalid query: %v", zap.Error(err))
		return nil, err
	}
	if !isSelect {
		d.logger.Error("Only SELECT statement is allowed", zap.String("query", sql))
		return nil, domain.ErrNotSelectStatement
	}

	countSql, err := pkg.BuildCountQuery(sql)
	if err != nil {
		d.logger.Error("Invalid query: %v", zap.Error(err))
		return nil, err
	}

	countResult, err := d.olap.Query(countSql)
	if err != nil {
		return nil, err
	}

	countResultMap, err := countResult.RowsToMap()
	if err != nil {
		return nil, err
	}

	count, ok := (*countResultMap)[0]["count_star()"].(int64)
	if !ok {
		return nil, fmt.Errorf("invalid count_star() value")
	}

	sql, err = pkg.ImposeLimits(sql, 1000)
	if err != nil {
		d.logger.Error("Invalid query: %v", zap.Error(err))
		return nil, err
	}

	result, err := d.olap.Query(sql)
	if err != nil {
		return nil, err
	}
	defer result.Close()

	resultMap, err := result.RowsToMap()
	if err != nil {
		return nil, err
	}

	return map[string]any{
		"total": count,
		"data":  resultMap,
	}, nil
}

func (d *OlapService) RestQuery(params models.RestParams) (map[string]any, error) {
	sql, err := pkg.BuildSelectQueryFromRestParams(params)
	if err != nil {
		return nil, err
	}

	countSql, err := pkg.BuildCountQuery(sql)
	if err != nil {
		return nil, err
	}

	countResult, err := d.olap.Query(countSql)
	if err != nil {
		return nil, err
	}

	countResultMap, err := countResult.RowsToMap()
	if err != nil {
		return nil, err
	}

	count := (*countResultMap)[0]["count_star()"].(int64)

	sql, err = pkg.ImposeLimits(sql, 1000)
	if err != nil {
		return nil, err
	}

	result, err := d.olap.Query(sql)

	resultMap, err := result.RowsToMap()
	return map[string]any{"total": count, "data": resultMap}, nil
}

func (d *OlapService) GetTableSchema(tableName string) ([]map[string]any, error) {
	schemaRes, err := d.olap.Query(fmt.Sprintf("desc %s", tableName))
	if err != nil {
		return nil, err
	}
	schema, err := schemaRes.RowsToMap()
	if err != nil {
		return nil, err
	}

	return *schema, nil
}

func (d *OlapService) ExecuteQuery(query string) ([]map[string]any, error) {
	res, err := d.olap.Query(query)
	if err != nil {
		return nil, err
	}

	mapRes, err := res.RowsToMap()
	if err != nil {
		return nil, err
	}

	return *mapRes, nil
}

func (d *OlapService) DropTable(tableName string) error {
	return d.olap.DropTable(tableName)
}
