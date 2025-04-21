package models

type UploadSchemaParams struct {
	ProjectID string
	DatasetID string
	FilePath  string
}

type AIAgentChatParams struct {
	ProjectIDs []string
	DatasetIDs []string
	UserInput  string
	DataChan   chan []byte
	ErrChan    chan error
}
