package services

import (
	"context"
	"fmt"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
)

type ChatService struct {
	store   repositories.ChatStoreRepository
	ai      repositories.AiChatRepository
	aiAgent repositories.AIAgentRepository
}

func NewChatService(store repositories.ChatStoreRepository, ai repositories.AiChatRepository, aiAgent repositories.AIAgentRepository) *ChatService {
	return &ChatService{store, ai, aiAgent}
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
	prevMsgs := &models.PaginationView[*models.ChatMessage]{}
	var err error
	if params.ChatID != "" {
		prevMsgs, err = service.GetChatMessages(params.ChatID, models.Pagination{Offset: 0, Limit: 100})
		if err != nil {
			return nil, fmt.Errorf("Error getting chat messages: %v", err)
		}
	}

	aiResponse, err := service.ai.GenerateChatResponse(context.Background(), params.Prompt, prevMsgs.Results)
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
	newUserMessage, err := service.store.AddNewMessage(context.Background(), params.ChatID, messages[len(messages)-2])
	if err != nil {
		return nil, fmt.Errorf("Error adding new message to chat: %v", err)
	}
	newMessage, err := service.store.AddNewMessage(context.Background(), params.ChatID, messages[len(messages)-1])
	if err != nil {
		return nil, fmt.Errorf("Error adding new message to chat: %v", err)
	}
	params.Messages = append(params.Messages, *newUserMessage, *newMessage)

	return &models.ChatWithMessages{
		Messages: params.Messages,
	}, nil
}

func (service *ChatService) ChatWithAiAgent(ctx context.Context, params *models.AIAgentChatParams) {
	service.aiAgent.Chat(ctx, params)
}
