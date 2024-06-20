package auth

import (
	"errors"
	"time"

	"github.com/factly/gopie/auth/models"
)

func (a *authImpl) CreateKey(m map[string]any) (*models.AuthKey, error) {
	token, err := generateAPIKey(a.masterKey)
	if err != nil {
		return nil, err
	}
	m["token"] = token
	key, err := a.db.CreateKey(m)
	return key, err
}

// TODO: Not fully functional
func (a *authImpl) UpdateKey(k string, m map[string]any) (*models.AuthKey, error) {
	if m == nil {
		return nil, errors.New("cannot update with nil body")
	}
	return a.db.UpdateKey(models.AuthToken(k), m)
}

func (a *authImpl) InvalidateKey(k string) error {
	_, err := a.db.UpdateKey(models.AuthToken(k), nil)
	return err
}

func (a *authImpl) GetKeyDetails(k string) (*models.AuthKey, error) {
	return a.db.GetKey(models.AuthToken(k))
}

func (a *authImpl) ListKeys(m map[string]string) ([]*models.AuthKey, error) {
	return a.db.ListKeys(m)
}

func (a *authImpl) DeleteKey(k string) error {
	return a.db.DeleteKey(models.AuthToken(k))
}

func (a *authImpl) ValidateKey(k string) (bool, error) {

	// validate the signature
	valid, err := validateAPIKey(k, a.masterKey)
	if err != nil {
		return valid, err
	}

	if !valid {
		return false, nil
	}

	// check expiry
	key, err := a.db.GetKey(models.AuthToken(k))
	if err != nil {
		return false, err
	}

	return key.ExpiresAt.After(time.Now()), nil
}

func (a *authImpl) DeleteAllKeys(m map[string]string) error {
	return a.db.DeleteAllKeys(m)
}

func (a *authImpl) GetMasterKey() string {
	return a.masterKey
}
