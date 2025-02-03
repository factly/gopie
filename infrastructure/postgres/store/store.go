package store

import (
	"context"
	"fmt"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"
)

type PostgresStore struct {
	pool   *pgxpool.Pool
	logger *logger.Logger
}

func NewPostgresStoreRepository(logger *logger.Logger) repositories.StoreRepository {
	return &PostgresStore{
		logger: logger,
	}
}

// Connect - Connect to Postgres
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
	return nil
}

func (store *PostgresStore) Close() error {
	if store.pool != nil {
		store.pool.Close()
	}
	return nil
}

func (store *PostgresStore) GetDB() interface{} {
	return store.pool
}
