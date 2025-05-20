package models

type UploadSchemaParams struct {
	ProjectID string `json:"project_id"`
	DatasetID string `json:"dataset_id"`
}

type AIAgentChatParams struct {
	ProjectIDs []string
	DatasetIDs []string
	UserInput  string
	DataChan   chan []byte
	ErrChan    chan error
}
