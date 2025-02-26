package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

type AiRepository interface {
	GenerateSql(nl string) (string, error)
}

type AiChatRepository interface {
	GenerateChatResponse(ctx context.Context, userMessage string) (*models.AiChatResponse, error)
}
