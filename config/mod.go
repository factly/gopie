package config

import (
	"log"

	"github.com/spf13/viper"
)

// struct for the config of entire application
type Config struct {
	Server ServerConfig
	Logger LoggerConfig
	Mode   ApplicationMode
	DuckDB map[string]any
}

// config for server
type ServerConfig struct {
	Port string
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

	if viper.IsSet("LOG_OUTPUT") {
		c.Server.Port = viper.GetString("LOG_OUTPUT")
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

	if viper.IsSet("DUCKDB_DSN") {
		c.DuckDB["dsn"] = viper.GetString("DUCKDB_DSN")
	} else {
		c.DuckDB["dsn"] = "./data/main.db"
		log.Println("❌ DUCKDB_DSN env not set, using './data/main.db' as default.")
	}

	return c, nil
}

func New() *Config {
	return &Config{}
}
