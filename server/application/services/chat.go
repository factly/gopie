package services

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/google/uuid"
)

type ChatService struct {
	store   repositories.ChatStoreRepository
	ai      repositories.AiChatRepository
	aiAgent repositories.AIAgentRepository
}

func NewChatService(store repositories.ChatStoreRepository, ai repositories.AiChatRepository, aiAgent repositories.AIAgentRepository) *ChatService {
	return &ChatService{store, ai, aiAgent}
}

func (service *ChatService) DeleteChat(id, createdBy, orgID string) error {
	return service.store.DeleteChat(context.Background(), id, createdBy, orgID)
}

func (service *ChatService) ListUserChats(userID, orgID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error) {
	return service.store.ListUserChats(context.Background(), userID, orgID, pagination)
}

func (service *ChatService) UpdateChat(chatID string, params *models.UpdateChatParams) (*models.Chat, error) {
	return service.store.UpdateChat(context.Background(), chatID, params)
}

func (service *ChatService) GetChatMessages(chatID string) ([]*models.ChatMessage, error) {
	return service.store.GetChatMessages(context.Background(), chatID)
}

func (service *ChatService) AddNewMessage(ctx context.Context, chatID string, messages []models.ChatMessage) ([]models.ChatMessage, error) {
	for i, msg := range messages {
		if msg.CreatedAt.IsZero() {
			messages[i].CreatedAt = time.Now()
		}
	}
	return service.store.AddNewMessage(ctx, chatID, messages)
}

func (service *ChatService) D_ChatWithAi(params *models.D_ChatWithAiParams) (*models.D_ChatWithMessages, error) {
	messages := params.Messages
	prevMsgs := &models.PaginationView[*models.D_ChatMessage]{}

	aiResponse, err := service.ai.GenerateChatResponse(context.Background(), params.Prompt, prevMsgs.Results)
	if err != nil {
		return nil, fmt.Errorf("Error generating chat response from ai: %v", err)
	}
	messages[len(messages)-1].CreatedAt = time.Now()
	messages = append(messages, models.D_ChatMessage{
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

		uuid, err := uuid.NewV6()
		chatWithMessages := &models.D_ChatWithMessages{
			ID:        uuid.String(),
			Name:      title.Response,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
			CreatedBy: params.CreatedBy,
			Messages:  messages,
		}

		return chatWithMessages, err
	}

	// existing chat
	params.Messages = append(params.Messages, messages[len(messages)-2], messages[len(messages)-1])

	return &models.D_ChatWithMessages{
		Messages: params.Messages,
	}, nil
}

func (service *ChatService) ChatWithAiAgent(ctx context.Context, params *models.AIAgentChatParams) {
	service.aiAgent.Chat(ctx, params)
}

func (service *ChatService) CreateChat(ctx context.Context, params *models.CreateChatParams) (*models.ChatWithMessages, error) {
	var userMessage *models.ChatMessage
	var filteredMessages []models.ChatMessage

	for _, msg := range params.Messages {
		if msg.Object == "user.message" {
			userMessage = &msg
		}
		if msg.Choices != nil && len(msg.Choices) > 0 {
			filteredMessages = append(filteredMessages, msg)
		}
	}
	if userMessage == nil {
		return nil, errors.New("no user message found in chat messages")
	}

	title, err := service.ai.GenerateTitle(ctx, *userMessage.Choices[0].Delta.Content)
	if err != nil {
		fmt.Printf("Error generating title from AI: %v\n", err)
		title = &models.D_AiChatResponse{
			Response: "Untitled Chat",
		}
	}

	params.Title = title.Response
	params.Messages = filteredMessages
	chat, err := service.store.CreateChat(ctx, params)
	return chat, err
}

func (service *ChatService) GetChatByID(chatID, userID string) (*models.Chat, error) {
	chat, err := service.store.GetChatByID(context.Background(), chatID, userID)
	if err != nil {
		return nil, fmt.Errorf("error getting chat by ID: %w", err)
	}
	return chat, nil
}

func (services *ChatService) UpdateChatVisibility(chatID, userID string, params *models.UpdateChatVisibilityParams) (*models.Chat, error) {
	chat, err := services.store.UpdateChatVisibility(context.Background(), chatID, userID, params)
	if err != nil {
		return nil, fmt.Errorf("error updating chat visibility: %w", err)
	}
	return chat, nil
}
