package openai

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/sashabaranov/go-openai"
	"go.uber.org/zap"
)

type OpenAIClient struct {
	client *openai.Client
	model  string
	logger *logger.Logger
}

type defaultHeaderTransport struct {
	Origin http.RoundTripper
	Header http.Header
}

func (t *defaultHeaderTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	for key, values := range t.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}
	return t.Origin.RoundTrip(req)
}

// Create new OpenAI client from config
func NewOpenAIClient(cfg config.OpenAIConfig, logger *logger.Logger) *OpenAIClient {
	// set OpenAI config headers for request
	header := http.Header{}

	for key, value := range pkg.ParseConfigOptions(cfg.Options, logger) {
		header.Set(key, value)
	}

	// create custom http client for OpenAI to work
	httpClient := &http.Client{
		Transport: &defaultHeaderTransport{
			Origin: http.DefaultTransport,
			Header: header,
		},
	}

	// X is used instead of an actual api_key because it is handled by the proxy
	oaConfig := openai.DefaultConfig(cfg.Apikey)
	oaConfig.HTTPClient = httpClient
	oaConfig.BaseURL = cfg.BaseUrl

	client := openai.NewClientWithConfig(oaConfig)
	model := cfg.AIModel
	logger.Info("OpenAI client initialized", zap.String("model", model))
	return &OpenAIClient{client, model, logger}
}

// GenerateResponseJSON is a generic function that generates a response from OpenAI
// and unmarshals it into the provided type T. It enforces JSON output format
// to ensure consistent structured responses.
func GenerateResponseJSON[T any](c *OpenAIClient, content string) (*T, error) {
	c.logger.Debug("generating JSON response from OpenAI", zap.String("model", c.model))
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	ctx := context.Background()

	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: []openai.ChatCompletionMessage{msgs},
		ResponseFormat: &openai.ChatCompletionResponseFormat{
			Type: openai.ChatCompletionResponseFormatTypeJSONObject,
		},
	})
	if err != nil {
		c.logger.Error("failed to generate response from OpenAI", zap.Error(err))
		return nil, err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI")
		return nil, domain.ErrFailedToGenerateSql
	}

	responseContent := res.Choices[0].Message.Content
	c.logger.Debug("received JSON response from OpenAI", zap.Int("content_length", len(responseContent)))

	var result T
	if err := json.Unmarshal([]byte(responseContent), &result); err != nil {
		c.logger.Error("failed to unmarshal OpenAI response",
			zap.Error(err),
			zap.String("response", responseContent))
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}

// GenerateResponseString is a non-generic version for backwards compatibility
// when you need a plain string response without JSON parsing
func (c *OpenAIClient) GenerateResponseString(content string) (string, error) {
	c.logger.Debug("generating string response from OpenAI", zap.String("model", c.model))
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	ctx := context.Background()

	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: []openai.ChatCompletionMessage{msgs},
	})
	if err != nil {
		c.logger.Error("failed to generate response from OpenAI", zap.Error(err))
		return "", err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI")
		return "", domain.ErrFailedToGenerateSql
	}

	responseContent := res.Choices[0].Message.Content
	c.logger.Debug("received response from OpenAI", zap.Int("content_length", len(responseContent)))

	return responseContent, nil
}

func (c *OpenAIClient) GenerateChatResponseFunc(userMsg string, prevMsgs []*models.D_ChatMessage) (string, error) {
	c.logger.Debug("generating chat response from OpenAI",
		zap.Int("previous_messages", len(prevMsgs)),
		zap.String("model", c.model))

	msgs := make([]openai.ChatCompletionMessage, 0, len(prevMsgs)+1)
	for _, msg := range prevMsgs {
		if msg.Role == "assistant" || msg.Role == "user" {
			msgs = append(msgs, openai.ChatCompletionMessage{
				Role:    msg.Role,
				Content: msg.Content,
			})
		}
	}
	latestMessage := openai.ChatCompletionMessage{
		Role:    "user",
		Content: userMsg,
	}
	msgs = append(msgs, latestMessage)

	ctx := context.Background()
	res, err := c.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: msgs,
	})
	if err != nil {
		c.logger.Error("failed to generate chat response from OpenAI", zap.Error(err))
		return "", err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI")
		return "", domain.ErrFailedToGenerateSql
	}

	responseContent := res.Choices[0].Message.Content
	c.logger.Debug("generated chat response from OpenAI",
		zap.Int("response_length", len(responseContent)))
	return responseContent, nil
}

func (c *OpenAIClient) GenerateSql(content string) (string, error) {
	c.logger.Debug("generating SQL from OpenAI")
	return c.GenerateResponseString(content)
}

func (c *OpenAIClient) GenerateChatResponse(ctx context.Context, userMessage string, prevMessages []*models.D_ChatMessage) (*models.D_AiChatResponse, error) {
	resp, err := c.GenerateChatResponseFunc(userMessage, prevMessages)
	if err != nil {
		return nil, err
	}

	return &models.D_AiChatResponse{
		Response: resp,
	}, nil
}

func (c *OpenAIClient) GenerateTitle(ctx context.Context, content string) (*models.D_AiChatResponse, error) {
	c.logger.Debug("generating title from OpenAI")
	systemPrompt := `
	!! IMPORTANT: In the response only provide the title of the content. Do not provide any other information. !!
		Generate a title for the following content:
	` + content

	resp, err := c.GenerateResponseString(systemPrompt)
	if err != nil {
		c.logger.Error("failed to generate title", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("generated title from OpenAI", zap.Int("title_length", len(resp)))
	return &models.D_AiChatResponse{
		Response: resp,
	}, nil
}

func (c *OpenAIClient) GenerateColumnDescriptions(ctx context.Context, rows string, summary string) (map[string]string, error) {
	c.logger.Debug("generating column descriptions from OpenAI")
	systemPrompt := `
	!! IMPORTANT: In the response only provide the column descriptions in JSON format. Do not provide any other information. !!
	The response must be a valid JSON object with column names as keys and descriptions as values.

	Valid format:
	{
		"column_name_1": "description of column 1",
		"column_name_2": "description of column 2",
		"column_name_n": "description of column n"
	}

	Generate column descriptions for the following rows and summary:
	Rows: ` + rows + `
	Summary: ` + summary

	result, err := GenerateResponseJSON[map[string]string](c, systemPrompt)
	if err != nil {
		c.logger.Error("failed to generate column descriptions", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("generated column descriptions from OpenAI", zap.Int("columns_count", len(*result)))
	return *result, nil
}

func (c *OpenAIClient) GenerateDatasetDescription(ctx context.Context, datasetName string, columnNames []string, columnDescriptions map[string]string, rows string, summary string) (string, error) {
	c.logger.Debug("generating dataset description from OpenAI",
		zap.String("dataset_name", datasetName),
		zap.Int("column_count", len(columnNames)))

	// Prepare column info for the prompt
	columnInfo := "Column Information:\n"
	for _, colName := range columnNames {
		if desc, exists := columnDescriptions[colName]; exists {
			columnInfo += fmt.Sprintf("- %s: %s\n", colName, desc)
		} else {
			columnInfo += fmt.Sprintf("- %s\n", colName)
		}
	}

	systemPrompt := fmt.Sprintf(`
	!! CRITICAL: The generated description MUST be less than 950 characters. This is a strict requirement - descriptions exceeding 950 characters will be rejected. !!

	Dataset Name: %s

	%s

	Sample Data (first few rows): %s

	Dataset Statistics: %s

	Based on the above information, generate a detailed and informative description for this dataset that:
	1. Explains what type of data it contains and its structure
	2. Mentions key columns and their purpose in detail
	3. Suggests multiple potential analytical use cases
	4. Describes the data's relevance and possible insights that can be derived

	IMPORTANT CONSTRAINTS:
	- Target length: 600-900 characters for optimal detail
	- MAXIMUM length: 950 characters (STRICTLY ENFORCED)
	- Provide ONLY the description text, no additional formatting or explanations
	`, datasetName, columnInfo, rows, summary)

	resp, err := c.GenerateResponseString(systemPrompt)
	if err != nil {
		c.logger.Error("failed to generate dataset description", zap.Error(err))
		return "", err
	}

	c.logger.Debug("generated dataset description from OpenAI",
		zap.Int("description_length", len(resp)))
	return resp, nil
}
