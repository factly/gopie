package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
)

type AiDriver struct {
	ai repositories.AiRepository
}

func NewAiDriver(ai repositories.AiRepository) *AiDriver {
	return &AiDriver{ai}
}

func (d *AiDriver) GenerateSql(query string) (string, error) {
	return d.ai.GenerateSql(query)
}

func (d *AiDriver) GenerateColumnDescriptions(rows string, summary string) (map[string]string, error) {
	return d.ai.GenerateColumnDescriptions(context.Background(), rows, summary)
}

func (d *AiDriver) GenerateDatasetDescription(datasetName string, columnNames []string, columnDescriptions map[string]string, rows string, summary string) (string, error) {
	return d.ai.GenerateDatasetDescription(context.Background(), datasetName, columnNames, columnDescriptions, rows, summary)
}
