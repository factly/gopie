package services

import (
	"context"
	"encoding/json"
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

func (d *OlapService) IngestS3File(ctx context.Context, s3Path string, name string, alterColumnNames map[string]string) (*models.UploadDatasetResult, error) {
	tableName := name
	if tableName == "" {
		tableName = fmt.Sprintf("gp_%s", pkg.RandomString(13))
	}
	// extract file format from s3Path
	parts := strings.Split(s3Path, "/")
	formatParts := strings.Split(parts[len(parts)-1], ".")
	format := formatParts[len(formatParts)-1]
	err := d.olap.CreateTableFromS3(s3Path, tableName, format, alterColumnNames)
	return &models.UploadDatasetResult{
		FilePath:  s3Path,
		Format:    format,
		Size:      0,
		TableName: tableName,
	}, err
}

func (d *OlapService) IngestFile(ctx context.Context, filepath string, name string, alterColumnNames map[string]string) (*models.UploadDatasetResult, error) {
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

	err = d.olap.CreateTable(filepath, tableName, format, alterColumnNames)
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
	// Check for truly empty identifiers (not just quoted ones)
	if strings.Contains(sql, `""`) && !strings.Contains(sql, `"""`) {
		parts := strings.Split(sql, `"`)
		for i := range len(parts) - 1 {
			if parts[i] == "" && i+1 < len(parts) && parts[i+1] == "" {
				return nil, fmt.Errorf("invalid SQL: query contains empty identifiers")
			}
		}
	}

	hasMultiple, err := pkg.HasMultipleStatements(sql)
	if err != nil {
		d.logger.Error("Invalid query", zap.Error(err))
		return nil, fmt.Errorf("failed to parse query: %w", err)
	}

	if hasMultiple {
		d.logger.Error("Multiple statements are not allowed", zap.String("query", sql))
		return nil, domain.ErrMultipleSqlStatements
	}

	isSelect, err := pkg.IsSelectStatement(sql)
	if err != nil {
		d.logger.Error("Invalid query", zap.Error(err))
		return nil, fmt.Errorf("failed to validate query type: %w", err)
	}
	if !isSelect {
		d.logger.Error("Only SELECT statement is allowed", zap.String("query", sql))
		return nil, domain.ErrNotSelectStatement
	}

	countSql, err := pkg.BuildCountQuery(sql)
	if err != nil {
		d.logger.Error("Invalid query", zap.Error(err))
		return nil, fmt.Errorf("failed to build count query: %w", err)
	}

	queryResult, err := d.getResultsWithCount(countSql, sql)
	if err != nil {
		d.logger.Error("Query execution failed", zap.Error(err))
		return nil, err
	}

	if queryResult == nil {
		return nil, fmt.Errorf("query execution returned no results")
	}

	return map[string]any{
		// "total": queryResult.Count,
		"data": queryResult.Rows,
	}, nil
}

// get dataset summary
func (d *OlapService) GetDatasetSummary(tableName string) (*[]models.DatasetSummary, error) {
	sql := fmt.Sprintf("summarize %s", tableName)
	rows, err := d.olap.Query(sql)
	if err != nil {
		return nil, err
	}
	summaryRes, err := rows.RowsToMap()
	if err != nil {
		d.logger.Error("Error converting rows to map", zap.Error(err))
		return nil, err
	}

	jsonSummary, _ := json.Marshal(summaryRes)

	var summary []models.DatasetSummary
	err = json.Unmarshal(jsonSummary, &summary)
	if err != nil {
		d.logger.Error("Error unmarshalling dataset summary", zap.Error(err))
		return nil, err
	}

	return &summary, nil
}

type queryResult struct {
	Rows *[]map[string]any
	// Count int64
	Err error
}

type asyncResult[T any] struct {
	data T
	err  error
}

func (d *OlapService) getResultsWithCount(countSql, sql string) (*queryResult, error) {
	// countChan := make(chan asyncResult[int64], 1)
	rowsChan := make(chan asyncResult[*[]map[string]any], 1)

	// go d.executeCountQuery(countSql, countChan)

	limitedSql, err := pkg.ImposeLimits(sql, 1000)
	if err != nil {
		return nil, fmt.Errorf("failed to impose limits: %w", err)
	}
	go d.executeDataQuery(limitedSql, rowsChan)

	// countResult := <-countChan
	// if countResult.err != nil {
	// 	return nil, fmt.Errorf("count query failed: %w", countResult.err)
	// }

	rowsResult := <-rowsChan
	if rowsResult.err != nil {
		return nil, fmt.Errorf("data query failed: %w", rowsResult.err)
	}

	return &queryResult{
		// Count: countResult.data,
		Rows: rowsResult.data,
	}, nil
}

func (d *OlapService) executeCountQuery(sql string, resultChan chan<- asyncResult[int64]) {
	var result asyncResult[int64]

	countResult, err := d.olap.Query(sql)
	if err != nil {
		result.err = fmt.Errorf("query execution failed: %w", err)
		resultChan <- result
		return
	}

	countResultMap, err := countResult.RowsToMap()
	if err != nil {
		result.err = fmt.Errorf("rows to map conversion failed: %w", err)
		resultChan <- result
		return
	}

	count, ok := (*countResultMap)[0]["count_star()"].(int64)
	if !ok {
		result.err = fmt.Errorf("invalid count_star() value type")
		resultChan <- result
		return
	}

	result.data = count
	resultChan <- result
}

func (d *OlapService) executeDataQuery(sql string, resultChan chan<- asyncResult[*[]map[string]any]) {
	var result asyncResult[*[]map[string]any]

	queryResult, err := d.olap.Query(sql)
	if err != nil {
		result.err = fmt.Errorf("query execution failed: %w", err)
		resultChan <- result
		return
	}
	defer queryResult.Close()

	resultMap, err := queryResult.RowsToMap()
	if err != nil {
		result.err = fmt.Errorf("rows to map conversion failed: %w", err)
		resultChan <- result
		return
	}

	result.data = resultMap
	resultChan <- result
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

	result, err := d.getResultsWithCount(countSql, sql)
	return map[string]any{
		// "total": result.Count,
		"data": result.Rows,
	}, nil
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
