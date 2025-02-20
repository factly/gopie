package s3

import (
	"fmt"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type httpHandler struct {
	logger     *logger.Logger
	olapSvc    *services.OlapService
	datasetSvc *services.DatasetService
	projectSvc *services.ProjectService
}

func (h *httpHandler) getMetrics(tableName string) (int, []map[string]interface{}, error) {
	countResChan := make(chan struct {
		count int64
		err   error
	})

	go func() {
		countSql := "select count(*) from " + tableName
		countResult, err := h.olapSvc.ExecuteQuery(countSql)
		if err != nil {
			countResChan <- struct {
				count int64
				err   error
			}{0, err}
			return
		}
		count, ok := countResult[0]["count_star()"].(int64)
		if !ok {
			h.logger.Error("Invalid count result type", zap.Any("count_result", countResult[0]["count_star()"]))
			countResChan <- struct {
				count int64
				err   error
			}{0, fmt.Errorf("Invalid count result type")}
			return
		}
		countResChan <- struct {
			count int64
			err   error
		}{count, nil}
	}()

	columnsResChan := make(chan struct {
		columns []map[string]interface{}
		err     error
	})
	// Get column descriptions
	go func() {
		columns, err := h.olapSvc.ExecuteQuery("desc " + tableName)
		columnsResChan <- struct {
			columns []map[string]interface{}
			err     error
		}{columns, err}
	}()

	countResult := <-countResChan
	if countResult.err != nil {
		return 0, nil, countResult.err
	}
	columnsRes := <-columnsResChan
	if columnsRes.err != nil {
		return 0, nil, columnsRes.err
	}

	return int(countResult.count), columnsRes.columns, nil
}

func Routes(router fiber.Router, olapSvc *services.OlapService, datasetSvc *services.DatasetService, projectSvc *services.ProjectService, logger *logger.Logger) {
	httpHandler := httpHandler{logger, olapSvc, datasetSvc, projectSvc}
	router.Post("/upload", httpHandler.upload)
	router.Post("/update", httpHandler.update)
}
