package services

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

const (
	APIKeyPrefix      = "gp"
	APIKeyTotalLength = 42
)

type ApikeyService struct {
	store  repositories.APIKeyStoreRepository
	logger *logger.Logger
}

func NewApikeyService(store repositories.APIKeyStoreRepository, logger *logger.Logger) *ApikeyService {
	return &ApikeyService{
		store:  store,
		logger: logger,
	}
}

// generateKey generates a new, secure API key using crypto/rand and encodes it with base64.URLEncoding.
// The output format is: prefix_randomstring. Returns the full API key and error if any.
func (s *ApikeyService) generateKey() (string, error) {
	sepLen := 1
	keyMaterialLen := APIKeyTotalLength - len(APIKeyPrefix) - sepLen
	keyBytes := max((keyMaterialLen*3)/4, 16) // ensure minimum entropy
	raw := make([]byte, keyBytes)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	encoded := base64.URLEncoding.WithPadding(base64.NoPadding).EncodeToString(raw)
	key := APIKeyPrefix + "_" + encoded
	if len(key) > APIKeyTotalLength {
		key = key[:APIKeyTotalLength]
	}
	return key, nil
}

// HashKey hashes the API key using SHA-256 and hex-encodes the result for secure storage.
func (s *ApikeyService) HashKey(apiKey string) string {
	hash := sha256.Sum256([]byte(apiKey))
	return hex.EncodeToString(hash[:])
}

// CreateAPIKey generates a new API key, stores its hash, and returns the created record with the plaintext key (shown only once).
func (s *ApikeyService) CreateAPIKey(ctx context.Context, params models.CreateAPIKeyParams) (*models.APIKeyResponse, error) {
	key, err := s.generateKey()
	if err != nil {
		s.logger.Error("Failed to generate API key", zap.Error(err))
		return nil, err
	}
	hash := s.HashKey(key)
	params.KeyHash = hash
	resp, err := s.store.Create(ctx, params)
	if err != nil {
		s.logger.Error("Failed to store API key", zap.Error(err))
		return nil, err
	}
	resp.Key = key // Only share key at creation
	return resp, nil
}

// DeleteAPIKey deletes an API key by id and orgID using the repository.
func (s *ApikeyService) DeleteAPIKey(ctx context.Context, id, orgID string) error {
	err := s.store.Delete(ctx, id, orgID)
	if err != nil {
		s.logger.Error("Failed to delete API key", zap.Error(err))
	}
	return err
}

// GetAPIKeyDetails fetches the API key details by id and orgID using the repository.
func (s *ApikeyService) GetAPIKeyDetails(ctx context.Context, id, orgID string) (*models.APIKey, error) {
	apiKey, err := s.store.Details(ctx, id, orgID)
	if err != nil {
		s.logger.Error("Failed to fetch API key details", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}

// GetAPIKeyByHash fetches the API key by hashed key and orgID using the repository.
func (s *ApikeyService) GetAPIKeyByHash(ctx context.Context, keyHash string) (*models.APIKey, error) {
	apiKey, err := s.store.GetByHash(ctx, keyHash)
	if err != nil {
		s.logger.Error("Failed to fetch API key by hash", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}

// ListExpiredAPIKeys fetches a paginated list of expired API keys for an orgID using the repository.
func (s *ApikeyService) ListExpiredAPIKeys(ctx context.Context, pagination models.Pagination, orgID string) (*models.PaginationView[*models.APIKey], error) {
	result, err := s.store.ListExpiredAPIKeys(ctx, pagination, orgID)
	if err != nil {
		s.logger.Error("Failed to list expired API keys", zap.Error(err))
		return nil, err
	}
	return result, nil
}

// SearchAPIKeys calls the repository to search for API keys by applicationID, query, pagination, and orgID.
func (s *ApikeyService) SearchAPIKeys(ctx context.Context, applicationID string, query string, pagination models.Pagination, orgID string) (*models.PaginationView[*models.APIKey], error) {
	result, err := s.store.SearchAPIKeys(ctx, query, pagination, orgID)
	if err != nil {
		s.logger.Error("Failed to search API keys", zap.Error(err))
		return nil, err
	}
	return result, nil
}

// UpdateLastUsedAPIKey updates the last used timestamp for the API key using the repository.
func (s *ApikeyService) UpdateLastUsedAPIKey(ctx context.Context, id, orgID string) (*models.APIKey, error) {
	apiKey, err := s.store.UpdateLastUsed(ctx, id, orgID)
	if err != nil {
		s.logger.Error("Failed to update last used for API key", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}

// RevokeAPIKey revokes an API key by id and orgID using the repository.
func (s *ApikeyService) RevokeAPIKey(ctx context.Context, id, orgID string) (*models.APIKey, error) {
	apiKey, err := s.store.Revoke(ctx, id, orgID)
	if err != nil {
		s.logger.Error("Failed to revoke API key", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}
