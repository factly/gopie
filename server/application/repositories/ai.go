package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

type AiRepository interface {
	GenerateSql(nl string, maxTokens *int) (string, error)
	GenerateColumnDescriptions(ctx context.Context, rows string, summary string, maxTokens *int) (map[string]string, error)
	GenerateDatasetDescription(ctx context.Context, datasetName string, columnNames []string, columnDescriptions map[string]string, rows string, summary string, maxTokens *int) (string, error)
}

type AiChatRepository interface {
	GenerateChatResponse(ctx context.Context, userMessage string, prevMessage []*models.D_ChatMessage, maxTokens *int) (*models.D_AiChatResponse, error)
	GenerateTitle(ctx context.Context, userMessage string, maxTokens *int) (*models.D_AiChatResponse, error)
}
