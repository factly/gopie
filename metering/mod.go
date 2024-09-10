package metering

import (
	"context"
	"time"

	meterus "github.com/elliot14A/meterus-go"
)

type MeteringClient struct {
	client    *meterus.MeterusClient
	eventType string
}

func NewMeteringClient(client *meterus.MeterusClient, eventType string) (*MeteringClient, error) {
	return &MeteringClient{client, eventType}, nil

}

func (m *MeteringClient) Ingest(endpoint, userID, organisationID, dataset, method, subject string) error {
	event, err := meterus.NewCloudEvent(
		// meterus assigns id
		"",
		// source
		"gopie.server",
		"1.0",
		m.eventType,
		time.Now(),
		subject,
		map[string]any{
			"user_id":         userID,
			"organisation_id": organisationID,
			"endpoint":        endpoint,
			"dataset":         dataset,
			"method":          method,
		},
	)
	if err != nil {
		return err
	}
	context := context.Background()
	return m.client.Ingest(context, event)
}
