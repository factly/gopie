package duckdb

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"strings"

	"github.com/c2h5oh/datasize"
	"github.com/factly/gopie/pkg"
)

type Driver struct {
	name string
}

func (d Driver) Open(cfgMap map[string]any, logger *pkg.Logger) (*Connection, error) {
	cfg, err := newConfig(cfgMap)
	if err != nil {
		return nil, err
	}
	logger.Info("opening duckdb handle...")

	if cfg.DBFilePath != "" {
		tmpPath := cfg.DBFilePath + ".tmp"
		_ = os.RemoveAll(tmpPath)

		walPath := cfg.DBFilePath + ".wal"
		if stat, err := os.Stat(walPath); err == nil {
			if stat.Size() >= 100*int64(datasize.MB) {
				_ = os.Remove(walPath)
			}
		}
	}

	if cfg.DBStoragePath != "" {
		if err := os.MkdirAll(cfg.DBStoragePath, fs.ModePerm); err != nil && !errors.Is(err, fs.ErrExist) {
			return nil, err
		}
	}

	olapSemSize := cfg.PoolSize - 1
	if olapSemSize < 1 {
		olapSemSize = 1
	}

	ctx := context.Background()

	c := &Connection{
		config:       cfg,
		ctx:          ctx,
		logger:       logger,
		driverConfig: cfgMap,
		driverName:   d.name,
	}

	err = c.reopenDB()
	if err != nil {
		if c.config.ErrorOnIncompatibleVersion || !strings.Contains(err.Error(), "created with an older, incompatible version of Gopie ") {
			return nil, err
		}

		c.logger.Logger.Debug("Resetting .db file because it was created with an older, incompatible version of rill")

		tmpPath := cfg.DBFilePath + ".tmp"
		_ = os.RemoveAll(tmpPath)
		walPath := cfg.DBFilePath + ".wal"
		_ = os.Remove(walPath)
		_ = os.Remove(cfg.DBFilePath)

		if err := c.reopenDB(); err != nil {
			return nil, err
		}
	}

	conn, err := c.db.Connx(context.Background())
	if err != nil && strings.Contains(err.Error(), "Symbol is not found") {
		fmt.Printf("Your version of macOs is not supported.")
		os.Exit(1)
	} else if err == nil {
		conn.Close()
	} else {
		return nil, err
	}

	return c, nil
}
