package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

type AIAgentRepository interface {
	UploadSchema(params *models.SchemaParams) error
	Chat(ctx context.Context, params *models.AIAgentChatParams)
	DeleteSchema(params *models.SchemaParams) error
}
