package duckdb

import (
	"context"
	"fmt"
	"strings"

	"github.com/factly/gopie/domain/pkg/config"
	"go.uber.org/zap"
)

// setupDuckDBHttpFs runs setup commands for local DuckDB, primarily for S3 (httpfs).
func (m *OlapDBDriver) setupDuckDBHttpFs(s3Cfg *config.S3Config) error {
	m.logger.Debug("starting post-connection setup for httpfs/S3")
	commands := m.generateHttpFsCommands()

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error("failed to begin transaction for httpfs setup", zap.Error(err))
		return fmt.Errorf("failed to begin transaction for httpfs setup: %w", err)
	}
	defer tx.Rollback() // Rollback if commit is not successful or if there's a panic

	for _, cmd := range commands {
		m.logger.Debug("executing httpfs setup command", zap.String("command", cmd))
		if _, err := tx.Exec(cmd); err != nil {
			m.logger.Error("failed to execute httpfs setup command",
				zap.String("command", cmd),
				zap.Error(err))
			return fmt.Errorf("failed executing httpfs setup command '%s': %w", cmd, err)
		}
	}

	if err := m.applyS3Settings(); err != nil {
		m.logger.Error("failed to apply S3 settings", zap.Error(err))
		return fmt.Errorf("failed to apply S3 settings: %w", err)
	}

	if err := tx.Commit(); err != nil {
		m.logger.Error("failed to commit transaction for httpfs setup", zap.Error(err))
		return fmt.Errorf("failed to commit httpfs setup: %w", err)
	}
	m.logger.Info("S3/httpfs configuration completed successfully",
		zap.String("endpoint", s3Cfg.Endpoint),
		zap.String("region", s3Cfg.Region),
		zap.Bool("ssl_enabled", s3Cfg.SSL))
	return nil
}

// generateHttpFsCommands generates the SQL commands for httpfs and extension loading only.
func (m *OlapDBDriver) generateHttpFsCommands() []string {
	// Only extension commands; S3 config handled via persistent secret
	return []string{
		"INSTALL httpfs;", "LOAD httpfs;",
		"INSTALL postgres;", "LOAD postgres;",
		"INSTALL mysql;", "LOAD mysql;",
	}
}

// applyS3Settings ensures a persistent S3 secret exists for DuckDB
func (m *OlapDBDriver) applyS3Settings() error {
	if m.s3Config == nil {
		return nil // No S3 config to apply
	}

	// Use a deterministic secret name based on S3 endpoint (could hash for more collision resistance)
	secretName := "gopie_s3_secret"
	row := m.db.QueryRow("SELECT COUNT(*) FROM duckdb_secrets() WHERE name = ?", secretName)
	var count int
	if err := row.Scan(&count); err != nil {
		return fmt.Errorf("error checking for persistent S3 secret: %w", err)
	}
	if count > 0 {
		// Drop the old persistent secret if it exists
		dropSecret := fmt.Sprintf("DROP PERSISTENT SECRET %s;", secretName)
		_, err := m.db.Exec(dropSecret)
		if err != nil {
			return fmt.Errorf("failed to drop persistent S3 secret: %w", err)
		}
		m.logger.Info("Dropped old DuckDB persistent S3 secret", zap.String("secretName", secretName))
	}

	endpoint := strings.TrimPrefix(m.s3Config.Endpoint, "http://")
	endpoint = strings.TrimPrefix(endpoint, "https://")

	// Always create the new persistent secret
	createSecret := fmt.Sprintf(`CREATE PERSISTENT SECRET %s (
			TYPE s3, 
			KEY_ID '%s', 
			SECRET '%s', 
			REGION '%s', 
			ENDPOINT '%s',
			USE_SSL %v,
			URL_STYLE 'path'
		);`,
		secretName,
		m.s3Config.AccessKey,
		m.s3Config.SecretKey,
		m.s3Config.Region,
		endpoint,
		m.s3Config.SSL,
	)
	_, err := m.db.Exec(createSecret)
	if err != nil {
		return fmt.Errorf("failed to create persistent S3 secret: %w", err)
	}
	m.logger.Info("Applied new DuckDB persistent S3 secret", zap.String("secretName", secretName))
	return nil
}
