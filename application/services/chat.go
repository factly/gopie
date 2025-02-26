package services

import (
	"context"
	"fmt"
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

func (service *ChatService) ChatWithAi(params *models.ChatWithAiParams) (*models.ChatWithMessages, error) {
	messages := params.Messages

	aiResponse, err := service.ai.GenerateChatResponse(context.Background(), params.Prompt)
	if err != nil {
		return nil, fmt.Errorf("Error generating chat response from ai: %v", err)
	}
	messages[len(messages)-1].CreatedAt = time.Now()
	messages = append(messages, models.ChatMessage{
		Content:   aiResponse.Response,
		Role:      "assistant",
		CreatedAt: time.Now(),
	})
	// new chat
	if params.ChatID == "" {

		title, err := service.ai.GenerateTitle(context.Background(), messages[len(messages)-1].Content)
		if err != nil {
			return nil, fmt.Errorf("Error generating title from ai: %v", err)
		}

		chat, err := service.store.CreateChat(context.Background(), &models.CreateChatParams{
			Messages:  messages,
			Name:      title.Response,
			CreatedBy: params.CreatedBy,
			DatasetID: params.DatasetID,
		})

		return chat, err
	}

	// existing chat
	newMessage, err := service.store.AddNewMessage(context.Background(), params.ChatID, messages[len(messages)-1])
	if err != nil {
		return nil, fmt.Errorf("Error adding new message to chat: %v", err)
	}

	return &models.ChatWithMessages{
		Messages: append(params.Messages, *newMessage),
	}, nil
}
