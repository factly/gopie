package download

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/domain/models"
)

func (r *downloadServerRepository) List(userID, orgID string, limit, offset int) ([]models.Download, error) {
	url := fmt.Sprintf("%s/downloads?limit=%d&offset=%d", r.baseURL, limit, offset)
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

	var downloads []models.Download
	if err := json.NewDecoder(resp.Body).Decode(&downloads); err != nil {
		return nil, err
	}
	return downloads, nil
}
