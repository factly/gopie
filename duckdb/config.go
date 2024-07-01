package duckdb

import (
	"fmt"
	"net/url"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/mitchellh/mapstructure"
)

const (
	cpuThreadRatio float64 = 0.5
	poolSizeMin    int     = 2
	poolSizeMax    int     = 5
)

// Config represents the DuckDB Config
type Config struct {
	// DSN is the connection string.
	DSN string `mapstructure:"dsn"`
	// Path is the path to the database file. If set, it will tke precedence over the path contained in DSN.
	// This is a convenience option for setting the path in a more human-readable way.
	Path string `mapstructure:"path"`
	// DataDir is the path to directory wher duckdb file named 'main.db' will be created. In case of external table storage all the files will also be present in DataDir's subdirectories.
	// If path is set then DataDir is ignored.
	DataDir string `mapstructure:"data_dir"`
	// PoolSize is the number of concurrent connections and queries allowed.
	PoolSize int `mapstructure:"pool_size"`
	// AllowHostAccess denotes whether to limit access to the local enviroment and file system.
	AllowHostAccess bool `mapstructure:"allow_host_access"`
	// ErrorOnIncompatibleVersion controls whether to return error or delete DBFile created with older duckdb version.
	ErrorOnIncompatibleVersion bool `mapstructure:"error_on_incompatible_version"`
	// ExtTableStorage controls if every table is stored in a different db file.
	ExtTableStorage bool `mapstructure:"external_table_storage"`
	// CPU cores available for the DB.
	CPU int `mapstructure:"cpu"`
	// MemoryLimitGB is the amout of memory available for the DB.
	MemoryLimitGB int `mapstructure:"memory_limit_gb"`
	// StorageLimitBytes is the amount disk storage available for the DB.
	StorageLimitBytes int64 `mapstructure:"storage_limit_bytes"`
	// MaxMemoryGBOverride sets a hard override for the "max_memory" DuckDB setting.
	MaxMemoryGBOverride int `mapstructure:"max_memory_gb_override"`
	// ThreadsOverride sets a hard override for the "threads" DuckDB setting. Set to -1 for unlimited threads.
	ThreadsOverride int `mapstructure:"threads_override"`
	// BootQueries is queries to run on boot. Use ; to separate multiple queries. Common use case is to provide project specific memory and threads ratios.
	BootQueries string `mapstructure:"boot_queries"`
	// DBFilePath is the path where the database is stored. It is inferred from the DSN (can't be provided by the user).
	DBFilePath string `mapstructure:"_"`
	// DBStoragePath is the path where the database files are stored. It is inferred from the DSN (can't be provided by the user).
	DBStoragePath string `mapstructure:"_"`
}

// create config from map[string]map
// returns an error if failed to create config
func newConfig(cfgMap map[string]any) (*Config, error) {
	cfg := &Config{}
	err := mapstructure.WeakDecode(cfgMap, cfg)
	if err != nil {
		return nil, fmt.Errorf("could not decode config: %w", err)
	}

	// duckdb supports in-memory features but gopie's wont scale when duckdb is set to memory
	// so it is ignored
	if strings.HasPrefix(cfg.DSN, ":memory:") {
		return nil, fmt.Errorf("in-memory database is not supported by 'gopie'")
	}

	// Parse DSB as URL
	uri, err := url.Parse(cfg.DSN)
	if err != nil {
		return nil, fmt.Errorf("could not parse dsn: %w", err)
	}

	qry, err := url.ParseQuery(uri.RawQuery)
	if err != nil {
		return nil, fmt.Errorf("could not parse dsn: %w", err)
	}

	if cfg.Path != "" {
		uri.Path = cfg.Path
	} else if cfg.DataDir != "" {
		uri.Path = filepath.Join(cfg.DataDir, "main.db")
	}

	cfg.DBFilePath = uri.Path
	cfg.DBStoragePath = filepath.Dir(cfg.DBFilePath)

	maxMemory := cfg.MemoryLimitGB
	if cfg.MaxMemoryGBOverride != 0 {
		maxMemory = cfg.MaxMemoryGBOverride
	}

	if maxMemory > 0 {
		qry.Add("max_memory", fmt.Sprintf("%dGB", maxMemory))
	}

	// Set thread limit
	var threads int
	if cfg.ThreadsOverride != 0 {
		threads = cfg.ThreadsOverride
	} else if cfg.CPU > 0 {
		threads = int(cpuThreadRatio * float64(cfg.CPU))
		if threads <= 0 {
			threads = 1
		}
	}

	if threads > 0 {
		qry.Add("threads", strconv.Itoa(threads))
	}

	// Set poolsize
	poolSize := cfg.PoolSize
	if qry.Has("gopie_pool_size") {
		val := qry.Get("gopie_pool_size")
		qry.Del("gopie_pool_size")

		poolSize, err = strconv.Atoi(val)
		if err != nil {
			return nil, fmt.Errorf("could not parse dsn: 'gopie_pool_size' is not an integer")
		}
	}

	if poolSize == 0 && threads != 0 {
		poolSize = threads
		if cfg.CPU != 0 && cfg.CPU < poolSize {
			poolSize = cfg.PoolSize
		}
		poolSize = min(poolSizeMax, poolSize)
	}
	poolSize = max(poolSizeMin, poolSize)
	cfg.PoolSize = poolSize

	cfg.DSN = fmt.Sprintf("%s?%s", uri.Path, qry.Encode())

	return cfg, nil
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
