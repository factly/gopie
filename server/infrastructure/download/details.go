package download

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/domain/models"
)

func (r *downloadServerRepository) Get(downloadID, userID, orgID string) (*models.Download, error) {
	url := fmt.Sprintf("%s/downloads/%s", r.baseURL, downloadID)
	httpReq, _ := http.NewRequest("GET", url, nil)
	httpReq.Header.Set("x-user-id", userID)
	httpReq.Header.Set("x-organization-id", orgID)

	resp, err := r.client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("server returned status %d", resp.StatusCode)
	}

	var download models.Download
	if err := json.NewDecoder(resp.Body).Decode(&download); err != nil {
		return nil, err
	}
	return &download, nil
}
