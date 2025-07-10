package models

import "time"

// INFO: deprecated will be removed in future versions
type D_Chat struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	CreatedBy string    `json:"created_by"`
}

type D_ChatWithMessages struct {
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	CreatedAt time.Time       `json:"created_at"`
	UpdatedAt time.Time       `json:"updated_at"`
	CreatedBy string          `json:"created_by"`
	Messages  []D_ChatMessage `json:"messages"`
}

type D_ChatWithAiParams struct {
	ChatID    string
	DatasetID string
	CreatedBy string
	Messages  []D_ChatMessage
	Prompt    string
}
type D_ChatMessage struct {
	ID        string    `json:"id"`
	Content   string    `json:"content"`
	Role      string    `json:"role"`
	CreatedAt time.Time `json:"created_at"`
}

type D_CreateChatParams struct {
	Name      string          `json:"name"`
	CreatedBy string          `json:"created_by"`
	Messages  []D_ChatMessage `json:"messages"`
	DatasetID string          `json:"dataset_id"`
}

type D_UpdateChatParams struct {
	Name string `json:"name"`
}

type UpdateChatParams struct {
	Title string `json:"name"`
}

type D_AiChatResponse struct {
	Response string `json:"response"`
}

type Chat struct {
	ID             string    `json:"id"`
	Title          string    `json:"title"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
	CreatedBy      string    `json:"created_by"`
	Visibility     string    `json:"visibility"`
	OrganizationID string    `json:"organization_id"`
}

type ChatMessage struct {
	ID        string    `json:"id"`
	ChatID    string    `json:"chat_id"`
	Choices   []Choice  `json:"choices"`
	CreatedAt time.Time `json:"created_at"`
	Model     string    `json:"model"`
	Object    string    `json:"object"`
}

type ChatWithMessages struct {
	ID             string        `json:"id"`
	Title          string        `json:"title"`
	CreatedAt      time.Time     `json:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at"`
	CreatedBy      string        `json:"created_by"`
	Messages       []ChatMessage `json:"messages"`
	Visibility     string        `json:"visibility"`
	OrganizationID string        `json:"organization_id"`
}

type CreateChatParams struct {
	ID             string        `json:"id"`
	Title          string        `json:"title"`
	CreatedBy      string        `json:"created_by"`
	Messages       []ChatMessage `json:"messages"`
	OrganizationID string        `json:"organization_id"`
}

type Choice struct {
	Delta        Delta   `json:"delta"`
	FinishReason *string `json:"finish_reason"`
	Index        int     `json:"index"`
	Logprobs     any     `json:"logprobs"`
}

type Delta struct {
	Content      *string       `json:"content"`
	FunctionCall *FunctionCall `json:"function_call"`
	Refusal      any           `json:"refusal"`
	Role         *string       `json:"role"`
	ToolCalls    []any         `json:"tool_calls"`
}

type FunctionCall struct {
	Arguments string `json:"arguments"`
	Name      string `json:"name"`
}

type ToolFunction struct {
	Arguments string `json:"arguments"`
	Name      string `json:"name"`
}

type UpdateChatVisibilityParams struct {
	OrganizationID string
	Visibility     string
}
