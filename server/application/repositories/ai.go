package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

type AiRepository interface {
	GenerateSql(nl string) (string, error)
}

type AiChatRepository interface {
	GenerateChatResponse(ctx context.Context, userMessage string, prevMessage []*models.D_ChatMessage) (*models.D_AiChatResponse, error)
	GenerateTitle(ctx context.Context, userMessage string) (*models.D_AiChatResponse, error)
}
