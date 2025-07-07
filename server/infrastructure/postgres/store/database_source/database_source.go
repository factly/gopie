package database_source

import (
	"context"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/crypto"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"
)

type DatabaseSourceStore struct {
	q      *gen.Queries
	logger *logger.Logger
	config *config.GopieConfig
	db     *pgxpool.Pool
}

// NewDatabaseSourceStore creates a new DatabaseSourceStore
func NewDatabaseSourceStore(db interface{}, logger *logger.Logger, config *config.GopieConfig) repositories.DatabaseSourceStoreRepository {
	return &DatabaseSourceStore{
		q:      gen.New(db.(*pgxpool.Pool)),
		logger: logger,
		config: config,
		db:     db.(*pgxpool.Pool),
	}
}

// Create creates a new database source
func (s *DatabaseSourceStore) Create(ctx context.Context, params models.CreateDatabaseSourceParams) (*models.DatabaseSource, error) {
	// Encrypt the connection string
	encryptedConnectionString, err := crypto.EncryptString(params.ConnectionString, []byte(s.config.EncryptionKey))
	if err != nil {
		s.logger.Error("Error encrypting connection string", zap.Error(err))
		return nil, err
	}

	row, err := s.q.CreateDatabaseSource(ctx, gen.CreateDatabaseSourceParams{
		ConnectionString: encryptedConnectionString,
		SqlQuery:         params.SQLQuery,
		Driver:           params.Driver,
		OrgID:            pgtype.Text{String: params.OrganizationID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error creating database source", zap.Error(err))
		return nil, err
	}

	return &models.DatabaseSource{
		ID:               row.ID.String(),
		ConnectionString: params.ConnectionString, // Return the original connection string, not the encrypted one
		SQLQuery:         row.SqlQuery,
		CreatedAt:        row.CreatedAt.Time.Format(time.RFC3339),
		UpdatedAt:        row.UpdatedAt.Time.Format(time.RFC3339),
	}, nil
}

// Get retrieves a database source by ID
func (s *DatabaseSourceStore) Get(ctx context.Context, id, orgID string) (*models.DatabaseSource, error) {
	parseUUID, _ := uuid.Parse(id)
	row, err := s.q.GetDatabaseSource(ctx, gen.GetDatabaseSourceParams{
		ID:    pgtype.UUID{Bytes: parseUUID, Valid: true},
		OrgID: pgtype.Text{String: orgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error getting database source", zap.Error(err))
		return nil, err
	}
	// Decrypt the connection string
	decryptedConnectionString, err := crypto.DecryptString(row.ConnectionString, []byte(s.config.EncryptionKey))
	if err != nil {
		s.logger.Error("Error decrypting connection string", zap.Error(err))
		return nil, err
	}

	return &models.DatabaseSource{
		ID:               row.ID.String(),
		ConnectionString: decryptedConnectionString,
		OrganizationID:   row.OrgID.String,
		SQLQuery:         row.SqlQuery,
		CreatedAt:        row.CreatedAt.Time.Format(time.RFC3339),
		UpdatedAt:        row.UpdatedAt.Time.Format(time.RFC3339),
	}, nil
}

// Delete deletes a database source
func (s *DatabaseSourceStore) Delete(ctx context.Context, id string) error {
	parseUUID, _ := uuid.Parse(id)
	err := s.q.DeleteDatabaseSource(ctx, pgtype.UUID{Bytes: parseUUID, Valid: true})
	if err != nil {
		s.logger.Error("Error deleting database source", zap.Error(err))
		return err
	}

	return nil
}

// List lists all database sources
func (s *DatabaseSourceStore) List(ctx context.Context, limit, offset int, orgID string) ([]*models.DatabaseSource, error) {
	rows, err := s.q.ListDatabaseSources(ctx, gen.ListDatabaseSourcesParams{
		Limit:  int32(limit),
		Offset: int32(offset),
		OrgID:  pgtype.Text{String: orgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error listing database sources", zap.Error(err))
		return nil, err
	}

	var result []*models.DatabaseSource
	for _, row := range rows {
		decryptedConnectionString, err := crypto.DecryptString(row.ConnectionString, []byte(s.config.EncryptionKey))
		if err != nil {
			s.logger.Error("Error decrypting connection string", zap.Error(err))
			return nil, err
		}

		result = append(result, &models.DatabaseSource{
			ID:               row.ID.String(),
			ConnectionString: decryptedConnectionString,
			OrganizationID:   row.OrgID.String,
			SQLQuery:         row.SqlQuery,
			CreatedAt:        row.CreatedAt.Time.Format(time.RFC3339),
			UpdatedAt:        row.UpdatedAt.Time.Format(time.RFC3339),
		})
	}

	return result, nil
}
