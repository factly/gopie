package aiagent

import (
	"net/http"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/logger"
)

type aiAgent struct {
	httpClient *http.Client
	url        string
	logger     *logger.Logger
}

func NewAIAgent(url string, logger *logger.Logger) repositories.AIAgentRepository {
	return &aiAgent{
		httpClient: &http.Client{},
		url:        url,
		logger:     logger,
	}
}

func (a *aiAgent) buildUrl(endpoint string, queryParams map[string][]string) string {
	// Construct the URL with query parameters
	url := a.url + endpoint
	if queryParams == nil {
		return url
	}

	if len(queryParams) > 0 {
		url += "?"
		for key, values := range queryParams {
			for _, value := range values {
				url += key + "=" + value + "&"
			}
		}
		url = url[:len(url)-1] // Remove the trailing '&'
	}

	return url
}
