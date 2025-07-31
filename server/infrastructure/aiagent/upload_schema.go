package aiagent

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/domain/models"
	"go.uber.org/zap"
)

func (a *aiAgent) UploadSchema(params *models.SchemaParams) error {
	bodyBuf, err := json.Marshal(params)
	if err != nil {
		a.logger.Error("Error in marshalling params to JSON", zap.Error(err))
		return err
	}

	url := a.buildUrl("/api/v1/upload_schema")
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(bodyBuf))
	if err != nil {
		a.logger.Error("Error in creating request to AI agent", zap.Error(err))
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	httpClient := http.Client{}
	resp, err := httpClient.Do(req)
	if err != nil {
		a.logger.Error("Error in sending request to AI agent", zap.Error(err))
		return err
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		a.logger.Error("Error in response from AI agent", zap.Int("status_code", resp.StatusCode))
		return fmt.Errorf("error in response from AI agent: %s", resp.Status)
	}

	var respBody struct {
		Message string `json:"message"`
		Success bool   `json:"success"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&respBody); err != nil {
		a.logger.Error("Error in decoding response from AI agent", zap.Error(err))
		return err
	}

	if !respBody.Success {
		a.logger.Error("Error in response from AI agent", zap.String("message", respBody.Message))
		return fmt.Errorf("error in response from AI agent: %s", respBody.Message)
	}

	a.logger.Debug("Schema uploaded successfully", zap.String("message", respBody.Message))

	return nil
}
