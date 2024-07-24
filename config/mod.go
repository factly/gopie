package config

import (
	"log"
	"strconv"

	"github.com/spf13/viper"
)

// struct for the config of entire application
type Config struct {
	Server  ServerConfig
	Logger  LoggerConfig
	Mode    ApplicationMode
	DuckDB  map[string]any
	Auth    AuthConfig
	OpenAI  OpenAIConfig
	S3      S3Config
	D       DetachCmdConfig
	PortKey map[string]any
}

// config for server
type ServerConfig struct {
	Port     string
	ReadOnly bool
}

type DetachCmdConfig struct {
	GopieUrl string
}

// config for auth
type AuthConfig struct {
	BboltPath string
	Mastkey   string
}

type OpenAIConfig struct {
	APIKey string
	Model  string
}

type S3Config struct {
	AccessKey       string
	SecretAccessKey string
	Endpoint        string
	Bucket          string
}

// config for application logger
type LoggerConfig struct {
	// define the output type for logger
	OutputType string
	// define logger level - Debug, Error
	Level string
}

// Enum for applicantion modes
type Mode int

const (
	DEV Mode = iota
	PROD
	STAG
)

// config for application mode
type ApplicationMode struct {
	Mode Mode
}

func StringToApplicationMode(value string) Mode {
	switch value {
	case "dev":
		return DEV
	case "prod":
		return PROD
	case "stag":
		return STAG
	default:
		return DEV
	}
}

func (config Config) LoadConfig() (*Config, error) {
	log.Println("⚙️ loading configuration for 🐹 gopie.")

	// set viper config to load envs
	viper.AddConfigPath(".")
	viper.SetConfigName("config")
	viper.SetEnvPrefix("gopie")
	viper.AutomaticEnv()

	err := viper.ReadInConfig()
	if err != nil {
		log.Println("❌ config file not found.")
	}
	c := &Config{}

	if viper.IsSet("SERVER_PORT") {
		c.Server.Port = viper.GetString("SERVER_PORT")
	} else {
		c.Server.Port = "8000"
		log.Println("❌ SERVER_PORT env not set, using '8000' as default.")
	}

	if viper.IsSet("READ_ONLY") {
		c.Server.ReadOnly = viper.GetBool("READ_ONLY")
	} else {
		log.Println("❌ READ_ONLY env not set, Gopie will run as read-only server")
		c.Server.ReadOnly = true
	}

	if viper.IsSet("LOG_OUTPUT") {
		c.Logger.OutputType = viper.GetString("LOG_OUTPUT")
	} else {
		c.Logger.OutputType = "stdout"
		log.Println("❌ LOG_OUTPUT env not set, using 'stdout' as default.")
	}

	if viper.IsSet("LOG_LEVEL") {
		c.Logger.Level = viper.GetString("LOG_LEVEL")
	} else {
		c.Logger.Level = "debug"
		log.Println("❌ LOG_LEVEL env not set, using 'debug' as default.")
	}

	if viper.IsSet("APPLICATION_MODE") {
		c.Mode.Mode = StringToApplicationMode(viper.GetString("APPLICATION_MODE"))
	} else {
		c.Mode.Mode = DEV
		log.Println("❌ APPLICATION_MODE env not set, using 'dev' as default.")
	}
	c.DuckDB = make(map[string]any)
	c.PortKey = make(map[string]any)

	if viper.IsSet("DUCKDB_DSN") {
		c.DuckDB["dsn"] = viper.GetString("DUCKDB_DSN")
	} else {
		c.DuckDB["dsn"] = "./data/main.db"
		log.Println("❌ DUCKDB_DSN env not set, using './data/main.db' as default.")
	}

	if viper.IsSet("DUCKDB_MEMORY_LIMIT") {
		c.DuckDB["memory_limit_gb"] = viper.GetInt("DUCKDB_MEMORY_LIMIT")
		if err != nil {
			// c.DuckDB["memory_limit_gb"] = 4
			// log.Println("❌ DUCKDB_MEMORY_LIMIT env is invalid, using '4gb' as default.")
		}
	} else {
		// set default max_memory to 4gb
		// c.DuckDB["memory_limit_gb"] = 4
		// log.Println("❌ DUCKDB_MAX_MEMORY env not set, using '4gb' as default.")
	}

	if viper.IsSet("DUCKDB_THREADS_LIMIT") {
		c.DuckDB["threads_override"], _ = strconv.Atoi(viper.GetString("DUCKDB_THREADS_LIMIT"))
	}

	if viper.IsSet("DUCKDB_CPU_LIMIT") {
		c.DuckDB["cpu"], _ = strconv.Atoi(viper.GetString("DUCKDB_CPU_LIMIT"))
	}

	if viper.IsSet("DUCKDB_POOL_SIZE") {
		c.DuckDB["cpu"], _ = strconv.Atoi(viper.GetString("DUCKDB_POOL_SIZE"))
	}

	if viper.IsSet("BBOLT_PATH") {
		c.Auth.BboltPath = viper.GetString("bbolt_path")
	} else {
		c.Auth.BboltPath = "./bbolt.db"
		log.Println("❌ BBOLT_PATH env not set, using './auth/bbolt.db' as default.")
	}

	if viper.IsSet("MASTER_KEY") {
		c.Auth.Mastkey = viper.GetString("MASTER_KEY")
	} else {
		c.Auth.Mastkey = "not_a_secure_master_key_please_change"
		log.Println("❌ MASTER_KEY env not set")
	}

	if viper.IsSet("OPEN_AI_API_KEY") {
		c.OpenAI.APIKey = viper.GetString("OPEN_AI_API_KEY")
	} else {
		log.Println("❌ OPEN_AI_API_KEY env not set")
	}

	// if viper.IsSet("OPEN_AI_MODEL") {
	// 	c.OpenAI.Model = viper.GetString("OPEN_AI_MODEL")
	// } else {
	// 	c.OpenAI.Model = "gpt3.5-turbo"
	// 	log.Println("❌ OPEN_AI_MODEL env not set, using 'gpt3.5-turbo' as default.")
	// }

	if viper.IsSet("S3_ACCESS_KEY") {
		c.S3.AccessKey = viper.GetString("S3_ACCESS_KEY")
	} else {
		log.Println("❌ S3_ACCESS_KEY env not set")
	}

	if viper.IsSet("S3_SECRET_ACCESS_KEY") {
		c.S3.SecretAccessKey = viper.GetString("S3_SECRET_ACCESS_KEY")
	} else {
		log.Println("❌ S3_SECRET_ACCESS_KEY env not set")
	}

	if viper.IsSet("S3_ENDPOINT") {
		c.S3.Endpoint = viper.GetString("S3_ENDPOINT")
	} else {
		log.Println("❌ S3_ENDPOINT env not set")
	}

	if viper.IsSet("GOPIE_SERVER_URL") {
		c.D.GopieUrl = viper.GetString("GOPIE_SERVER_URL")
	} else {
		c.D.GopieUrl = "http://localhost:8000"
		log.Println("❌ GOPIE_SERVER_URL env not set, using 'http://localhost:8000' as default")
	}

	if viper.IsSet("PORT_KEY_API_KEY") {
		c.PortKey["portkey_api_key"] = viper.GetString("PORT_KEY_API_KEY")
	} else {
		log.Println("❌ PORT_KEY_API_KEY env is not set")
	}

	if viper.IsSet("PORT_KEY_VIRTUAL_KEY") {
		c.PortKey["portkey_virtual_key"] = viper.GetString("PORT_KEY_VIRTUAL_KEY")
	} else {
		log.Println("❌ PORT_KEY_VIRTUAL_KEY env is not set")
	}

	if viper.IsSet("PORT_KEY_BASE_URL") {
		c.PortKey["portkey_base_url"] = viper.GetString("PORT_KEY_BASE_URL")
	} else {
		log.Println("❌ PORT_KEY_BASE_URL env is not set")
	}

	if viper.IsSet("PORT_KEY_AI_MODEL") {
		c.PortKey["ai_model"] = viper.GetString("PORT_KEY_AI_MODEL")
	} else {
		log.Println("❌ PORT_KEY_AI_MODEL env is not set, using gpt-4o-mini as default")
		c.PortKey["ai_model"] = "gpt-4o-mini"
	}

	return c, nil
}

func New() *Config {
	return &Config{}
}
