package metering

import (
	"context"
	"time"

	meterus "github.com/elliot14A/meterus-go/client"
)

type MeteringClient struct {
	service   *meterus.MeteringService
	eventType string
}

func NewMeteringClient(client *meterus.Client, eventType string) (*MeteringClient, error) {
	service := client.NewMeteringService()
	return &MeteringClient{service, eventType}, nil

}

func (m *MeteringClient) Ingest(endpoint, userID, organisationID, dataset, method string) error {
	event, err := meterus.NewCloudEvent(
		// meterus assigns id
		"",
		// source
		"gopie.server",
		"1.0",
		m.eventType,
		time.Now(),
		organisationID,
		map[string]any{
			"user_id":  userID,
			"endpoint": endpoint,
			"dataset":  dataset,
			"method":   method,
		},
	)
	if err != nil {
		return err
	}
	context := context.Background()
	return m.service.Ingest(context, event)
}
