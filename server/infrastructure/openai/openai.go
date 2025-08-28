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

	for key, value := range pkg.ParseConfigOptions(cfg.Options) {
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

func (c *OpenAIClient) GenerateResponse(content string) (string, error) {
	c.logger.Debug("generating sql from OpenAI")
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
		c.logger.Error("failed to generate sql from OpenAI", zap.Error(err))
		return "", err
	}

	if len(res.Choices) == 0 {
		return "", domain.ErrFailedToGenerateSql
	}
	return res.Choices[0].Message.Content, nil
}

func (c *OpenAIClient) GenerateChatResponseFunc(userMsg string, prevMsgs []*models.D_ChatMessage) (string, error) {
	c.logger.Debug("generating sql from OpenAI")
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
		// Temperature: 0.2,
	})
	if err != nil {
		return "", err
	}
	if len(res.Choices) == 0 {
		return "", domain.ErrFailedToGenerateSql
	}
	c.logger.Debug("generated sql from OpenAI", zap.String("sql", res.Choices[0].Message.Content))
	return res.Choices[0].Message.Content, nil
}

func (c *OpenAIClient) GenerateSql(content string) (string, error) {
	return c.GenerateResponse(content)
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
	systemPrompt := `
	!! IMPORTANT: In the response only provide the title of the content. Do not provide any other information. !!
		Generate a title for the following content:
	` + content

	resp, err := c.GenerateResponse(systemPrompt)
	if err != nil {
		return nil, err
	}

	return &models.D_AiChatResponse{
		Response: resp,
	}, nil
}

func (c *OpenAIClient) GenerateColumnDescriptions(ctx context.Context, rows string, summary string) (map[string]string, error) {
	systemPrompt := `
	!! IMPORTANT: In the response only provide the column descriptions in JSON format. Do not provide any other information. !!
	Valid format is:
	{
		"column_name_1": "description of column 1",
		"column_name_2": "description of column 2",
		...
		"column_name_n": "description of column n"
	}
	Invalid format is:
	response: {
		"column_name_1": "description of column 1",
		"column_name_2": "description of column 2",
		...
		"column_name_n": "description of column n"
	}
	or
	result: {
		"column_name_1": "description of column 1",
		"column_name_2": "description of column 2",
		...
		"column_name_n": "description of column n"
	}
	and so on.

	Generate column descriptions for the following rows and summary:
	Rows: ` + rows + `
	Summary: ` + summary

	resp, err := c.GenerateResponse(systemPrompt)
	if err != nil {
		return nil, err
	}
	// Parse the response into a map
	descriptions := make(map[string]string)
	// conver string to map
	err = json.Unmarshal([]byte(resp), &descriptions)
	if err != nil {
		c.logger.Error("failed to parse column descriptions", zap.Error(err))
		return nil, err
	}

	return descriptions, nil
}

func (c *OpenAIClient) GenerateDatasetDescription(ctx context.Context, datasetName string, columnNames []string, columnDescriptions map[string]string, rows string, summary string) (string, error) {
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

	resp, err := c.GenerateResponse(systemPrompt)
	if err != nil {
		c.logger.Error("failed to generate dataset description", zap.Error(err))
		return "", err
	}

	return resp, nil
}
