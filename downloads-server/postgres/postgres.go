package postgres

import (
	"context"
	"fmt"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"
)

type PostgresStore struct {
	pool   *pgxpool.Pool
	logger *logger.Logger
	q      *gen.Queries
}

func NewPostgresStore(logger *logger.Logger) *PostgresStore {
	return &PostgresStore{
		logger: logger,
	}
}

func (store *PostgresStore) Connect(cfg *config.PostgresConfig) error {
	store.logger.Info("Connecting to Postgres", zap.String("host", cfg.Host), zap.String("port", cfg.Port), zap.String("database", cfg.Database))
	dsn := fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.Database)

	config, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		store.logger.Error("Error parsing postgres config", zap.Error(err))
		return err
	}

	ctx := context.Background()
	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		store.logger.Error("Error connecting to Postgres", zap.Error(err))
		return err
	}

	// Verify connection
	if err := pool.Ping(ctx); err != nil {
		store.logger.Error("Error pinging Postgres", zap.Error(err))
		pool.Close()
		return err
	}

	store.pool = pool
	store.logger.Info("Connected to Postgres")
	store.q = gen.New(pool)
	return nil
}

func (store *PostgresStore) Close() error {
	if store.pool != nil {
		store.pool.Close()
	}
	return nil
}

func (store *PostgresStore) GetDB() *pgxpool.Pool {
	return store.pool
}

func (s *PostgresStore) CreateDownload(ctx context.Context, req *models.CreateDownloadRequest) (*models.Download, error) {
	genParams := req.ToGenCreateDownloadParams()

	genDownload, err := s.q.CreateDownload(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// GetDownload retrieves a single download by its ID and organization ID.
func (s *PostgresStore) GetDownload(ctx context.Context, id, orgID string) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.GetDownloadParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	}

	genDownload, err := s.q.GetDownload(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// ListDownloadsByUser retrieves a paginated list of downloads for a specific user.
func (s *PostgresStore) ListDownloadsByUser(ctx context.Context, userID, orgID string, limit, offset int32) ([]*models.Download, error) {
	genParams := gen.ListDownloadsByUserParams{
		UserID: userID,
		OrgID:  orgID,
		Limit:  limit,
		Offset: offset,
	}

	genDownloads, err := s.q.ListDownloadsByUser(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownloadSlice(genDownloads), nil
}

// ListPendingDownloads retrieves all downloads with a 'pending' status for processing.
func (s *PostgresStore) ListPendingDownloads(ctx context.Context) ([]*models.Download, error) {
	genDownloads, err := s.q.ListPendingDownloads(ctx)
	if err != nil {
		return nil, err
	}
	return models.FromGenDownloadSlice(genDownloads), nil
}

// SetDownloadToProcessing updates a download's status to 'processing'.
func (s *PostgresStore) SetDownloadToProcessing(ctx context.Context, id string) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genDownload, err := s.q.SetDownloadToProcessing(ctx, pgtype.UUID{Bytes: uid, Valid: true})
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// SetDownloadAsCompleted updates a download's status to 'completed' with its result metadata.
func (s *PostgresStore) SetDownloadAsCompleted(ctx context.Context, id string, req *models.SetDownloadCompletedRequest) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.SetDownloadAsCompletedParams{
		ID:           pgtype.UUID{Bytes: uid, Valid: true},
		PreSignedUrl: pgtype.Text{String: req.PreSignedURL, Valid: true},
		ExpiresAt:    pgtype.Timestamptz{Time: req.ExpiresAt, Valid: true},
	}

	genDownload, err := s.q.SetDownloadAsCompleted(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// SetDownloadAsFailed updates a download's status to 'failed' with an error message.
func (s *PostgresStore) SetDownloadAsFailed(ctx context.Context, id string, req *models.SetDownloadFailedRequest) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.SetDownloadAsFailedParams{
		ID:           pgtype.UUID{Bytes: uid, Valid: true},
		ErrorMessage: pgtype.Text{String: req.ErrorMessage, Valid: true},
	}

	genDownload, err := s.q.SetDownloadAsFailed(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// DeleteDownload removes a download record from the database.
func (s *PostgresStore) DeleteDownload(ctx context.Context, id, orgID string) error {
	uid, err := uuid.Parse(id)
	if err != nil {
		return err
	}

	genParams := gen.DeleteDownloadParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	}

	return s.q.DeleteDownload(ctx, genParams)
}
