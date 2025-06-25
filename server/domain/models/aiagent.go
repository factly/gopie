package models

type UploadSchemaParams struct {
	ProjectID string `json:"project_id"`
	DatasetID string `json:"dataset_id"`
}

type AIChatMessage struct {
	Content string `json:"content"`
	Role    string `json:"role"`
}

type AIAgentChatParams struct {
	ProjectIDs   string
	DatasetIDs   string
	Messages     []AIChatMessage
	PrevMessages []AIChatMessage
	DataChan     chan []byte
	ErrChan      chan error
}
