package openai

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"time"

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
// maxTokens is optional - pass nil to use default, or a pointer to an int to limit tokens
func GenerateResponseJSON[T any](c *OpenAIClient, content string, maxTokens *int) (*T, error) {
	c.logger.Debug("generating JSON response from OpenAI", zap.String("model", c.model))
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	ctx := context.Background()

	req := openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: []openai.ChatCompletionMessage{msgs},
		ResponseFormat: &openai.ChatCompletionResponseFormat{
			Type: openai.ChatCompletionResponseFormatTypeJSONObject,
		},
	}

	if maxTokens != nil {
		req.MaxTokens = *maxTokens
	}

	res, err := c.client.CreateChatCompletion(ctx, req)
	if err != nil {
		c.logger.Error("failed to generate response from OpenAI", zap.Error(err))
		return nil, err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI",
			zap.String("full_response", fmt.Sprintf("%+v", res)))
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
// maxTokens is optional - pass nil to use default, or a pointer to an int to limit tokens
func (c *OpenAIClient) GenerateResponseString(content string, maxTokens *int) (string, error) {
	c.logger.Debug("generating string response from OpenAI", zap.String("model", c.model))
	msgs := openai.ChatCompletionMessage{
		Role:    "user",
		Content: content,
	}

	ctx := context.Background()

	req := openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: []openai.ChatCompletionMessage{msgs},
	}

	if maxTokens != nil {
		req.MaxTokens = *maxTokens
	}

	res, err := c.client.CreateChatCompletion(ctx, req)
	if err != nil {
		c.logger.Error("failed to generate response from OpenAI", zap.Error(err))
		return "", err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI",
			zap.String("full_response", fmt.Sprintf("%+v", res)))
		return "", domain.ErrFailedToGenerateSql
	}

	responseContent := res.Choices[0].Message.Content
	c.logger.Debug("received response from OpenAI", zap.Int("content_length", len(responseContent)))

	return responseContent, nil
}

func (c *OpenAIClient) GenerateChatResponseFunc(userMsg string, prevMsgs []*models.D_ChatMessage, maxTokens *int) (string, error) {
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
	req := openai.ChatCompletionRequest{
		Model:    c.model,
		Messages: msgs,
	}

	if maxTokens != nil {
		req.MaxTokens = *maxTokens
	}

	res, err := c.client.CreateChatCompletion(ctx, req)
	if err != nil {
		c.logger.Error("failed to generate chat response from OpenAI", zap.Error(err))
		return "", err
	}

	if len(res.Choices) == 0 {
		c.logger.Error("no response choices returned from OpenAI",
			zap.String("full_response", fmt.Sprintf("%+v", res)))
		return "", domain.ErrFailedToGenerateSql
	}

	responseContent := res.Choices[0].Message.Content
	c.logger.Debug("generated chat response from OpenAI",
		zap.Int("response_length", len(responseContent)))
	return responseContent, nil
}

func (c *OpenAIClient) GenerateSql(content string, maxTokens *int) (string, error) {
	c.logger.Debug("generating SQL from OpenAI")
	return c.GenerateResponseString(content, maxTokens)
}

func (c *OpenAIClient) GenerateChatResponse(ctx context.Context, userMessage string, prevMessages []*models.D_ChatMessage, maxTokens *int) (*models.D_AiChatResponse, error) {
	resp, err := c.GenerateChatResponseFunc(userMessage, prevMessages, maxTokens)
	if err != nil {
		return nil, err
	}

	return &models.D_AiChatResponse{
		Response: resp,
	}, nil
}

func (c *OpenAIClient) GenerateTitle(ctx context.Context, content string, maxTokens *int) (*models.D_AiChatResponse, error) {
	c.logger.Debug("generating title from OpenAI")
	systemPrompt := `
	!! IMPORTANT: In the response only provide the title of the content. Do not provide any other information. !!
		Generate a title for the following content:
	` + content

	resp, err := c.GenerateResponseString(systemPrompt, maxTokens)
	if err != nil {
		c.logger.Error("failed to generate title", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("generated title from OpenAI", zap.Int("title_length", len(resp)))
	return &models.D_AiChatResponse{
		Response: resp,
	}, nil
}

func (c *OpenAIClient) GenerateColumnDescriptions(ctx context.Context, rows string, summary string, maxTokens *int) (map[string]string, error) {
	c.logger.Debug("generating column descriptions from OpenAI")

	const maxRetries = 3
	basePrompt := `
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

	var lastError error
	var result *map[string]string

	for attempt := 1; attempt <= maxRetries; attempt++ {
		c.logger.Debug("attempting to generate column descriptions",
			zap.Int("attempt", attempt),
			zap.Int("max_retries", maxRetries))

		systemPrompt := basePrompt
		if lastError != nil {
			// Add error feedback to the prompt for retry
			systemPrompt = fmt.Sprintf(`%s

!! PREVIOUS ATTEMPT FAILED !!
The previous response was invalid with the following error: %s

Please generate a valid JSON response following the exact format specified above. Ensure:
1. The response is valid JSON
2. All keys are column names from the provided data
3. All values are descriptive strings
4. No additional text or formatting outside the JSON object`, basePrompt, lastError.Error())

			c.logger.Warn("retrying with error feedback",
				zap.Int("attempt", attempt),
				zap.String("previous_error", lastError.Error()))
		}

		result, lastError = GenerateResponseJSON[map[string]string](c, systemPrompt, maxTokens)
		if lastError == nil && result != nil && len(*result) > 0 {
			c.logger.Debug("successfully generated column descriptions",
				zap.Int("columns_count", len(*result)),
				zap.Int("attempt", attempt))
			return *result, nil
		}

		if lastError != nil {
			c.logger.Warn("failed to generate column descriptions",
				zap.Error(lastError),
				zap.Int("attempt", attempt))
		} else if result != nil && len(*result) == 0 {
			lastError = fmt.Errorf("received empty column descriptions map")
			c.logger.Warn("received empty column descriptions",
				zap.Int("attempt", attempt))
		}

		// Apply exponential backoff before retrying (unless this was the last attempt)
		if attempt < maxRetries {
			// Exponential backoff: 2^(attempt-1) seconds with a cap at 16 seconds
			backoffDuration := time.Duration(math.Pow(2, float64(attempt-1))) * time.Second
			if backoffDuration > 16*time.Second {
				backoffDuration = 16 * time.Second
			}
			c.logger.Debug("backing off before retry",
				zap.Duration("backoff_duration", backoffDuration),
				zap.Int("attempt", attempt))
			time.Sleep(backoffDuration)
		}
	}

	c.logger.Error("exhausted all retries for generating column descriptions",
		zap.Int("max_retries", maxRetries),
		zap.Error(lastError))
	return nil, fmt.Errorf("failed to generate column descriptions after %d attempts: %w", maxRetries, lastError)
}

func (c *OpenAIClient) GenerateDatasetDescription(ctx context.Context, datasetName string, columnNames []string, columnDescriptions map[string]string, rows string, summary string, maxTokens *int) (string, error) {
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

	resp, err := c.GenerateResponseString(systemPrompt, maxTokens)
	if err != nil {
		c.logger.Error("failed to generate dataset description", zap.Error(err))
		return "", err
	}

	c.logger.Debug("generated dataset description from OpenAI",
		zap.Int("description_length", len(resp)))
	return resp, nil
}
