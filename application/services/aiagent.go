package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
)

type AIService struct {
	repository repositories.AIAgentRepository
}

func NewAIService(repository repositories.AIAgentRepository) *AIService {
	return &AIService{
		repository: repository,
	}
}

func (s *AIService) UploadSchema(params *models.UploadSchemaParams) error {
	err := s.repository.UploadSchema(params)
	if err != nil {
		return err
	}
	return nil
}

func (s *AIService) Chat(ctx context.Context, params *models.AIAgentChatParams) {
	s.repository.Chat(ctx, params)
}
