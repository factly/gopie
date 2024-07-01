package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"strings"

	"github.com/factly/gopie/auth/bbolt"
	"github.com/factly/gopie/auth/models"
	"github.com/factly/gopie/pkg"
)

type IAuth interface {
	CreateKey(m map[string]any) (*models.AuthKey, error)
	UpdateKey(k string, m map[string]any) (*models.AuthKey, error)
	InvalidateKey(k string) error
	GetKeyDetails(k string) (*models.AuthKey, error)
	ListKeys(m map[string]string) ([]*models.AuthKey, error)
	DeleteKey(k string) error
	ValidateKey(k string) (bool, error)
	DeleteAllKeys(m map[string]string) error
	GetMasterKey() string
}

type authImpl struct {
	logger    *pkg.Logger
	db        *bbolt.Bbolt
	masterKey string
}

func NewAuth(path string, logger *pkg.Logger, masterKey string) IAuth {
	db, err := bbolt.NewBboltInstance(path, logger)
	if err != nil {
		logger.Error("Error create new bbolt instance.: %s", err.Error())
		return nil
	}
	return &authImpl{logger, db, masterKey}
}

func generateAPIKey(masterKey string) (string, error) {
	prefix := pkg.RandomString(14)
	prefixBase64 := fmt.Sprintf("%s", base64.RawStdEncoding.EncodeToString([]byte(prefix)))

	h := hmac.New(sha256.New224, []byte(masterKey))

	h.Write([]byte(prefixBase64))
	signature := h.Sum(nil)

	apiKey := fmt.Sprintf("gp%s.%s", prefixBase64, base64.RawURLEncoding.EncodeToString(signature))

	return apiKey, nil
}

func validateAPIKey(apiKey string, masterKey string) (bool, error) {
	parts := strings.Split(apiKey, ".")
	if len(parts) != 2 {
		return false, fmt.Errorf("invalid api key format")
	}

	prefixBase64 := parts[0][2:]
	signatureBase64 := parts[1]

	_, err := base64.RawStdEncoding.DecodeString(prefixBase64)
	if err != nil {
		return false, fmt.Errorf("error decoding data part: %v", err)
	}

	h := hmac.New(sha256.New224, []byte(masterKey))
	h.Write([]byte(prefixBase64))
	expectedSignature := h.Sum(nil)

	provideSignature, err := base64.RawURLEncoding.DecodeString(signatureBase64)
	if err != nil {
		return false, fmt.Errorf("error decoding signature: %v", err)
	}

	if !hmac.Equal(expectedSignature, provideSignature) {
		return false, nil
	}

	return true, nil
}
