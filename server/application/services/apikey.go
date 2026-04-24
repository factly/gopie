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

func (s *ApikeyService) generateKey() (string, error) {
	sepLen := 1
	keyMaterialLen := APIKeyTotalLength - len(APIKeyPrefix) - sepLen
	keyBytes := max((keyMaterialLen*3)/4, 16)
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

func (s *ApikeyService) HashKey(apiKey string) string {
	hash := sha256.Sum256([]byte(apiKey))
	return hex.EncodeToString(hash[:])
}

func (s *ApikeyService) CreateAPIKey(ctx context.Context, params models.CreateAPIKeyParams) (*models.APIKeyResponse, error) {
	key, err := s.generateKey()
	if err != nil {
		s.logger.Critical("Failed to generate API key", zap.Error(err))
		return nil, err
	}
	hash := s.HashKey(key)
	params.KeyHash = hash
	resp, err := s.store.Create(ctx, params)
	if err != nil {
		s.logger.Critical("Failed to store API key", zap.Error(err))
		return nil, err
	}
	resp.Key = key
	return resp, nil
}

func (s *ApikeyService) DeleteAPIKey(ctx context.Context, id string) error {
	err := s.store.Delete(ctx, id)
	if err != nil {
		s.logger.Error("Failed to delete API key", zap.Error(err))
	}
	return err
}

func (s *ApikeyService) GetAPIKeyByHash(ctx context.Context, keyHash string) (*models.APIKey, error) {
	apiKey, err := s.store.GetByHash(ctx, keyHash)
	if err != nil {
		s.logger.Error("Failed to fetch API key by hash", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}

func (s *ApikeyService) SearchAPIKeys(ctx context.Context, query string, pagination models.Pagination) (*models.PaginationView[*models.APIKey], error) {
	result, err := s.store.SearchAPIKeys(ctx, query, pagination)
	if err != nil {
		s.logger.Error("Failed to search API keys", zap.Error(err))
		return nil, err
	}
	return result, nil
}

func (s *ApikeyService) UpdateLastUsedAPIKey(ctx context.Context, id string) (*models.APIKey, error) {
	apiKey, err := s.store.UpdateLastUsed(ctx, id)
	if err != nil {
		s.logger.Error("Failed to update last used for API key", zap.Error(err))
		return nil, err
	}
	return apiKey, nil
}
