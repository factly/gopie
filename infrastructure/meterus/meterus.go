package meterus

import (
	"context"

	meterus_ "github.com/elliot14A/meterus-go/client"
	"github.com/factly/gopie/application/repositories"
)

type MeterusApiKeyValidator struct {
	service *meterus_.ValidationService
}

func NewMeterusApiKeyValidator(client *meterus_.Client) repositories.ApiKeyRepository {
	service := client.NewValidationService()
	return &MeterusApiKeyValidator{service: service}
}

func (a *MeterusApiKeyValidator) Validate(key string) (bool, error) {
	_, _, _, err := a.service.ValidateApiKey(context.Background(), key, []string{"meterus:gopie"})
	if err != nil {
		return false, err
	}
	return true, nil
}
