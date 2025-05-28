package aiagent

// SSEEvent represents a server-sent event from the AI agent
type SSEEvent struct {
	ChatID           string  `json:"chat_id"`
	TraceID          string  `json:"trace_id"`
	Message          Message `json:"message"`
	DatasetsUsed     any     `json:"datasets_used,omitempty"`
	GenerateSQLQuery any     `json:"generate_sql_query,omitempty"`
	Error            *struct {
		Message string `json:"message"`
		Type    string `json:"type"`
	} `json:"error,omitempty"`
}

// Message contains the data associated with an SSE event
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
	Type    string `json:"type"`
}
