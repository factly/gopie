package download

import (
	"fmt"
	"net/http"
)

func (r *downloadServerRepository) Delete(downloadID, userID, orgID string) error {
	url := fmt.Sprintf("%s/downloads/%s", r.baseURL, downloadID)
	httpReq, _ := http.NewRequest("DELETE", url, nil)
	httpReq.Header.Set("x-user-id", userID)
	httpReq.Header.Set("x-organization-id", orgID)

	resp, err := r.client.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("server returned status %d", resp.StatusCode)
	}
	return nil
}
