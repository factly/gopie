package download

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/factly/gopie/domain/models"
)

func (r *downloadServerRepository) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
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

	dataChan := make(chan models.DownloadsSSEData)

	go func() {
		defer resp.Body.Close()
		defer close(dataChan)

		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			dataChan <- models.DownloadsSSEData{Data: append(scanner.Bytes(), '\n')}
		}

		if err := scanner.Err(); err != nil {
			dataChan <- models.DownloadsSSEData{Error: err}
		}
	}()

	return dataChan, nil
}
