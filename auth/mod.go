package auth

import (
	"context"
	"fmt"

	meterus "github.com/elliot14A/meterus-go/client"
)

type IAPIKey interface {
	ValidateKey(k string) (string, error)
}

type MeterusAPIKey struct {
	serivce *meterus.ValidationService
}

func NewAuth(client *meterus.Client) (IAPIKey, error) {
	service := client.NewValidationService()
	return &MeterusAPIKey{service}, nil
}

func (a *MeterusAPIKey) ValidateKey(k string) (string, error) {

	_, subject, _, err := a.serivce.ValidateApiKey(context.Background(), k, []string{"meterus:gopie"})
	if err != nil {
		fmt.Println(err)
		return "", err
	}

	return subject, nil
}
