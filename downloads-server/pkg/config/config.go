package config

import (
	"fmt"
	"log"

	"github.com/spf13/viper"
)

type ServerConfig struct {
	Host string
	Port string
}

type S3Config struct {
	AccessKey string
	SecretKey string
	Region    string
	Endpoint  string
	Bucket    string
	SSL       bool
}

type QueueConfig struct {
	NumWorkers int
	QueueSize  int
}

type LoggerConfig struct {
	Level   string
	LogFile string
	Mode    string
}

type Config struct {
	Server   ServerConfig
	S3       S3Config
	Logger   LoggerConfig
	OlapDB   OlapDBConfig
	Postgres PostgresConfig
	Queue    QueueConfig
}

type OlapDBConfig struct {
	DB         string
	MotherDuck *MotherDuckConfig
	DuckDB     *DuckDBConfig
}

type DuckDBConfig struct {
	Path string
}

type MotherDuckConfig struct {
	DBName          string
	Token           string
	HelperDBDirPath string
}

type PostgresConfig struct {
	Host     string
	Port     string
	Database string
	User     string
	Password string
}

func initializeViper() error {
	viper.SetConfigName("config")
	viper.SetConfigType("env")
	viper.AddConfigPath(".")
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		log.Printf("Error reading config file: %s", err)
		log.Println("Using environment variables")
		return nil
	}
	return nil
}

func validateConfig(config *Config) (*Config, error) {
	type validation struct {
		value string
		name  string
	}

	validations := []validation{
		{config.Postgres.Host, "postgres host"},
		{config.Postgres.Port, "postgres port"},
		{config.Postgres.Database, "postgres database"},
		{config.Postgres.User, "postgres user"},
		{config.Postgres.Password, "postgres password"},
	}

	if config.OlapDB.DB == "" {
		return nil, fmt.Errorf("missing olapdb dbtype")
	}

	switch config.OlapDB.DB {
	case "duckdb":
		config.OlapDB.DuckDB = &DuckDBConfig{
			Path: viper.GetString("GOPIE_DS_DUCKDB_PATH"),
		}

		// check it path exists
		if config.OlapDB.DuckDB.Path == "" {
			return nil, fmt.Errorf("missing DuckDB path")
		}

	case "motherduck":
		config.OlapDB.MotherDuck = &MotherDuckConfig{
			DBName:          viper.GetString("GOPIE_DS_MOTHERDUCK_DB_NAME"),
			Token:           viper.GetString("GOPIE_DS_MOTHERDUCK_TOKEN"),
			HelperDBDirPath: viper.GetString("GOPIE_DS_MOTHERDUCK_HELPER_DB_DIR_PATH"),
		}
		validations = append(validations,
			validation{config.OlapDB.MotherDuck.DBName, "MotherDuck DB name"},
			validation{config.OlapDB.MotherDuck.Token, "MotherDuck token"},
		)

	default:
		return nil, fmt.Errorf("invalid olapdb dbtype: %s", config.OlapDB.DB)
	}

	for _, v := range validations {
		if v.value == "" {
			return nil, fmt.Errorf("missing %s", v.name)
		}
	}

	return config, nil
}

func setDefaults() {
	viper.SetDefault("GOPIE_DS_SERVER_HOST", "localhost")
	viper.SetDefault("GOPIE_DS_SERVER_PORT", "8000")
	viper.SetDefault("GOPIE_DS_S3_REGION", "us-east-1")
	viper.SetDefault("GOPIE_DS_S3_SSL", false)
	viper.SetDefault("GOPIE_DS_LOGGER_LEVEL", "info")
	viper.SetDefault("GOPIE_DS_LOGGER_FILE", "gopie.log")
	viper.SetDefault("GOPIE_DS_LOGGER_MODE", "dev")
	viper.SetDefault("GOPIE_DS_DUCKDB_PATH", "./duckdb/gopie.db")
	viper.SetDefault("GOPIE_DS_QUEUE_SIZE", 1000)
	viper.SetDefault("GOPIE_DS_QUEUE_WORKERS", 10)
}

func LoadConfig() (*Config, error) {
	if err := initializeViper(); err != nil {
		return nil, err
	}

	setDefaults()

	config := &Config{
		Server: ServerConfig{
			Host: viper.GetString("GOPIE_DS_SERVER_HOST"),
			Port: viper.GetString("GOPIE_DS_SERVER_PORT"),
		},
		S3: S3Config{
			AccessKey: viper.GetString("GOPIE_DS_S3_ACCESS_KEY"),
			SecretKey: viper.GetString("GOPIE_DS_S3_SECRET_KEY"),
			Region:    viper.GetString("GOPIE_DS_S3_REGION"),
			Endpoint:  viper.GetString("GOPIE_DS_S3_ENDPOINT"),
			Bucket:    viper.GetString("GOPIE_DS_S3_BUCKET"),
			SSL:       viper.GetBool("GOPIE_DS_S3_SSL"),
		},
		Logger: LoggerConfig{
			Level:   viper.GetString("GOPIE_DS_LOGGER_LEVEL"),
			LogFile: viper.GetString("GOPIE_DS_LOGGER_FILE"),
			Mode:    viper.GetString("GOPIE_DS_LOGGER_MODE"),
		},
		OlapDB: OlapDBConfig{
			DB: viper.GetString("GOPIE_DS_OLAPDB_DBTYPE"),
		},
		Postgres: PostgresConfig{
			Host:     viper.GetString("GOPIE_DS_POSTGRES_HOST"),
			Port:     viper.GetString("GOPIE_DS_POSTGRES_PORT"),
			Database: viper.GetString("GOPIE_DS_POSTGRES_DB"),
			User:     viper.GetString("GOPIE_DS_POSTGRES_USER"),
			Password: viper.GetString("GOPIE_DS_POSTGRES_PASSWORD"),
		},
		Queue: QueueConfig{
			NumWorkers: viper.GetInt("GOPIE_DS_QUEUE_WORKERS"),
			QueueSize:  viper.GetInt("GOPIE_DS_QUEUE_SIZE"),
		},
	}

	var err error
	if config, err = validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}
