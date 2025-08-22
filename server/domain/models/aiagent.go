package models

type SchemaParams struct {
	ProjectID string `json:"project_id"`
	DatasetID string `json:"dataset_id"`
}

type AIChatMessage struct {
	Content   string `json:"content"`
	Role      string `json:"role"`
	ToolCalls []any  `json:"tool_calls"`
}

type AIAgentChatParams struct {
	ProjectIDs   string
	DatasetIDs   string
	Messages     []AIChatMessage
	PrevMessages []AIChatMessage
	DataChan     chan []byte
	ErrChan      chan error
}
