package models

import "time"

type Chat struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	CreatedBy string    `json:"created_by"`
}

type ChatWithMessages struct {
	ID        string        `json:"id"`
	Name      string        `json:"name"`
	CreatedAt time.Time     `json:"created_at"`
	UpdatedAt time.Time     `json:"updated_at"`
	CreatedBy string        `json:"created_by"`
	Messages  []ChatMessage `json:"messages"`
}

type ChatWithAiParams struct {
	ChatID    string        `json:"id,omitempty"`
	DatasetID string        `json:"dataset_id,omitempty"`
	UserID    string        `json:"user_id,omitempty"`
	Messages  []ChatMessage `json:"messages"`
}
type ChatMessage struct {
	ID        string    `json:"id"`
	Content   string    `json:"content"`
	Role      string    `json:"role"`
	CreatedAt time.Time `json:"created_at"`
}

type CreateChatParams struct {
	Name      string        `json:"name"`
	CreatedBy string        `json:"created_by"`
	Messages  []ChatMessage `json:"messages"`
	DatasetID string        `json:"dataset_id"`
}

type UpdateChatParams struct {
	Name string `json:"name"`
}

type AiChatResponse struct {
	Response string `json:"response"`
}
