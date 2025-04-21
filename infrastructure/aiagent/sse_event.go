package aiagent

// SSEEvent represents a server-sent event from the AI agent
type SSEEvent struct {
	EventNode string    `json:"event_node"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	EventData EventData `json:"event_data"`
}

// EventData contains the data associated with an SSE event
type EventData struct {
	Input  any `json:"input"`
	Result any `json:"result"`
	Error  any `json:"error"`
}
