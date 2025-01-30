package store

import (
	"database/sql"
	"fmt"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

type PostgresStore struct {
	db     *sql.DB
	logger *logger.Logger
}

func NewPostgresStoreRepository(logger *logger.Logger) repositories.StoreRepository {
	return &PostgresStore{
		logger: logger,
	}
}

// Connect - Connect to Postgres
func (store *PostgresStore) Connect(cfg *config.PostgresConfig) error {
	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable", cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Database)
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		store.logger.Error("Error connecting to Postgres", zap.Error(err))
		return err
	}
	store.db = db
	return nil
}

func (store *PostgresStore) Close() error {
	return store.db.Close()
}

func (store *PostgresStore) GetDB() *sql.DB {
	return store.db
}
