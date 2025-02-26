package services

import (
	"context"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
)

type ChatService struct {
	store repositories.ChatStoreRepository
	ai    repositories.AiChatRepository
}

func NewChatService(store repositories.ChatStoreRepository, ai repositories.AiChatRepository) *ChatService {
	return &ChatService{store, ai}
}

func (service *ChatService) CreateChat(params *models.CreateChatParams) (*models.ChatWithMessages, error) {
	aiResponse, err := service.ai.GenerateChatResponse(context.Background(), params.Messages[0].Content)
	if err != nil {
		return nil, err
	}
	params.Messages = append(params.Messages, models.ChatMessage{
		Content:   aiResponse.Response,
		Role:      "assistant",
		CreatedAt: time.Now(),
	})

	return service.store.CreateChat(context.Background(), params)
}

func (service *ChatService) DeleteChat(id string) error {
	return service.store.DeleteChat(context.Background(), id)
}

func (service *ChatService) DetailsChat(id string) (*models.Chat, error) {
	return service.store.DetailsChat(context.Background(), id)
}

func (service *ChatService) ListUserChats(userID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	return service.store.ListUserChats(context.Background(), userID, pagination)
}

func (service *ChatService) UpdateChat(chatID string, params *models.UpdateChatParams) (*models.Chat, error) {
	return service.store.UpdateChat(context.Background(), chatID, params)
}

func (service *ChatService) GetChatMessages(chatID string, pagination models.Pagination) (*models.PaginationView[*models.ChatMessage], error) {
	return service.store.GetChatMessages(context.Background(), chatID, pagination)
}

func (service *ChatService) GetChatsByDatasetID(datasetID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	return service.store.GetChatsByDatasetID(context.Background(), datasetID, pagination)
}

func (service *ChatService) AddNewMessage(chatID string, message models.ChatMessage) (*models.ChatMessage, error) {
	message.CreatedAt = time.Now()
	return service.store.AddNewMessage(context.Background(), chatID, message)
}

func (service *ChatService) DeleteMessage(chatID string, messageID string) error {
	return service.store.DeleteMessage(context.Background(), chatID, messageID)
}
