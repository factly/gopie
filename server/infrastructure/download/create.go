package download

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/factly/gopie/domain/models"
)

func (r *downloadRepository) CreateAndStream(req *models.CreateDownloadRequest) (io.ReadCloser, error) {
	url := fmt.Sprintf("%s/downloads", r.baseURL)

	payload, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	httpReq, err := http.NewRequest("POST", url, bytes.NewBuffer(payload))
	if err != nil {
		return nil, fmt.Errorf("failed to create http request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-user-id", req.UserID)
	httpReq.Header.Set("x-organization-id", req.OrgID)

	resp, err := r.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}

	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("downloads server returned an error: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	return resp.Body, nil
}
