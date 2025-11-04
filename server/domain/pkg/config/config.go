package config

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

type ServerConfig struct {
	Host string
	Port string
}

type InternalServerConfig struct {
	Host string
	Port string
}

type APIServerConfig struct {
	Host string
	Port string
}

type MeterusConfig struct {
	Addr   string
	ApiKey string
}

type S3Config struct {
	AccessKey string
	SecretKey string
	Region    string
	Endpoint  string
	SSL       bool
}

type LoggerConfig struct {
	Level   string
	LogFile string
	Mode    string
}

type CORSConfig struct {
	AllowOrigins     string
	AllowMethods     string
	AllowHeaders     string
	AllowCredentials bool
	MaxAge           int
}

type GopieConfig struct {
	Server          ServerConfig
	S3              S3Config
	Logger          LoggerConfig
	OlapDB          OlapDBConfig
	OpenAI          OpenAIConfig
	Meterus         MeterusConfig
	Postgres        PostgresConfig
	Zitadel         ZitadelConfig
	AIAgent         AIAgentConfig
	InternalServer  InternalServerConfig
	APIServer       APIServerConfig
	EnableZitadel   bool
	DownloadsServer DownloadsConfig
	EncryptionKey   string
	MainCORS        CORSConfig
	InternalCORS    CORSConfig
	APICORS         CORSConfig
	CORSEnabled     bool
}

type OlapDBConfig struct {
	DB         string
	MotherDuck *MotherDuckConfig
	DuckDB     *DuckDBConfig
	AccessMode string
}

type DuckDBConfig struct {
	Path         string
	CPU          int
	MemoryLimit  int
	StorageLimit int
}

type MotherDuckConfig struct {
	DBName          string
	Token           string
	HelperDBDirPath string
}

type OpenAIConfig struct {
	Options string
	Apikey  string
	BaseUrl string
	AIModel string
}

type PostgresConfig struct {
	Host     string
	Port     string
	Database string
	User     string
	Password string
}

type AIAgentConfig struct {
	Url string
}

type DownloadsConfig struct {
	Bucket string
}

type ZitadelConfig struct {
	Protocol     string
	Domain       string
	InsecurePort string
	ProjectID    string
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

func validateConfig(config *GopieConfig) (*GopieConfig, error) {
	type validation struct {
		value string
		name  string
	}

	validations := []validation{
		// Openai Options is optional
		{config.OpenAI.Apikey, "OpenAI api key"},
		{config.OpenAI.BaseUrl, "OpenAI base url"},
		{config.OpenAI.AIModel, "OpenAI ai model"},
		{config.Postgres.Host, "postgres host"},
		{config.Postgres.Port, "postgres port"},
		{config.Postgres.Database, "postgres database"},
		{config.Postgres.User, "postgres user"},
		{config.Postgres.Password, "postgres password"},
		{config.AIAgent.Url, "ai agent url"},
		{config.EncryptionKey, "encryption key"},
	}

	if config.EnableZitadel {
		validations = append(validations,
			validation{config.Zitadel.Protocol, "zitadel protocol"},
			validation{config.Zitadel.Domain, "zitadel domain"},
			validation{config.Zitadel.ProjectID, "zitadel project id"},
		)
		if viper.GetString("GOPIE_ZITADEL_PROTOCOL") != "https" {
			validations = append(validations, validation{config.Zitadel.InsecurePort, "zitadel insecure port"})
		}
	}

	validations = append(validations, validation{config.DownloadsServer.Bucket, "downloads bucket name"})

	if config.OlapDB.DB == "" {
		return nil, fmt.Errorf("missing olapdb dbtype")
	}

	switch config.OlapDB.DB {
	case "duckdb":
		config.OlapDB.DuckDB = &DuckDBConfig{
			Path:         viper.GetString("GOPIE_DUCKDB_PATH"),
			CPU:          viper.GetInt("GOPIE_DUCKDB_CPU"),
			MemoryLimit:  viper.GetInt("GOPIE_DUCKDB_MEMORY_LIMIT"),
			StorageLimit: viper.GetInt("GOPIE_DUCKDB_STORAGE_LIMIT"),
		}

		// check it path exists
		if config.OlapDB.DuckDB.Path == "" {
			return nil, fmt.Errorf("missing DuckDB path")
		}

		// INFO: path should exist if access mode is read_only
		// we create the directory if access mode is read_write
		if config.OlapDB.AccessMode == "read_write" {
			if err := ensureDirectoryExists(config.OlapDB.DuckDB.Path); err != nil {
				return nil, err
			}
		}

		if config.OlapDB.DuckDB.CPU <= 0 {
			return nil, fmt.Errorf("DuckDB CPU must be greater than 0")
		}
		if config.OlapDB.DuckDB.MemoryLimit <= 0 {
			return nil, fmt.Errorf("DuckDB memory limit must be greater than 0")
		}
		if config.OlapDB.DuckDB.StorageLimit <= 0 {
			return nil, fmt.Errorf("DuckDB storage limit must be greater than 0")
		}

	case "motherduck":
		config.OlapDB.MotherDuck = &MotherDuckConfig{
			DBName:          viper.GetString("GOPIE_MOTHERDUCK_DB_NAME"),
			Token:           viper.GetString("GOPIE_MOTHERDUCK_TOKEN"),
			HelperDBDirPath: viper.GetString("GOPIE_MOTHERDUCK_HELPER_DB_DIR_PATH"),
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

func ensureDirectoryExists(path string) error {
	dir := filepath.Dir(path)

	_, err := os.Stat(dir)
	if os.IsNotExist(err) {
		err := os.MkdirAll(dir, 0755)
		if err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
		log.Printf("Created directory: %s", dir)
	} else if err != nil {
		return fmt.Errorf("error checking directory %s: %w", dir, err)
	}

	return nil
}

func setDefaults() {
	viper.SetDefault("GOPIE_SERVER_HOST", "localhost")
	viper.SetDefault("GOPIE_SERVER_PORT", "8000")
	viper.SetDefault("GOPIE_INTERNAL_SERVER_HOST", "localhost")
	viper.SetDefault("GOPIE_INTERNAL_SERVER_PORT", "8001")
	viper.SetDefault("GOPIE_API_SERVER_HOST", "localhost")
	viper.SetDefault("GOPIE_API_SERVER_PORT", "8002")
	viper.SetDefault("GOPIE_S3_REGION", "us-east-1")
	viper.SetDefault("GOPIE_S3_SSL", false)
	viper.SetDefault("GOPIE_LOGGER_LEVEL", "info")
	viper.SetDefault("GOPIE_LOGGER_FILE", "gopie.log")
	viper.SetDefault("GOPIE_LOGGER_MODE", "dev")
	viper.SetDefault("GOPIE_OLAPDB_ACCESS_MODE", "read_write")
	viper.SetDefault("GOPIE_DUCKDB_CPU", 1)
	viper.SetDefault("GOPIE_ENABLE_ZITADEL", false)
	viper.SetDefault("GOPIE_DUCKDB_MEMORY_LIMIT", 1024)
	viper.SetDefault("GOPIE_DUCKDB_STORAGE_LIMIT", 1024)
	viper.SetDefault("GOPIE_DUCKDB_PATH", "./duckdb/gopie.db")
	viper.SetDefault("GOPIE_MOTHERDUCK_HELPER_DB_DIR_PATH", "./motherduck")
	viper.SetDefault("GOPIE_DOWNLOADS_USE_SERVER", false)

	// Default CORS settings for main server
	viper.SetDefault("GOPIE_MAIN_CORS_ALLOW_ORIGINS", "*")
	viper.SetDefault("GOPIE_MAIN_CORS_ALLOW_METHODS", "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS")
	viper.SetDefault("GOPIE_MAIN_CORS_ALLOW_HEADERS", "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id")
	viper.SetDefault("GOPIE_MAIN_CORS_ALLOW_CREDENTIALS", false)
	viper.SetDefault("GOPIE_MAIN_CORS_MAX_AGE", 86400)

	// Default CORS settings for internal server
	viper.SetDefault("GOPIE_INTERNAL_CORS_ALLOW_ORIGINS", "*")
	viper.SetDefault("GOPIE_INTERNAL_CORS_ALLOW_METHODS", "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS")
	viper.SetDefault("GOPIE_INTERNAL_CORS_ALLOW_HEADERS", "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id")
	viper.SetDefault("GOPIE_INTERNAL_CORS_ALLOW_CREDENTIALS", false)
	viper.SetDefault("GOPIE_INTERNAL_CORS_MAX_AGE", 86400)

	// Default CORS settings for API server
	viper.SetDefault("GOPIE_API_CORS_ALLOW_ORIGINS", "*")
	viper.SetDefault("GOPIE_API_CORS_ALLOW_METHODS", "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS")
	viper.SetDefault("GOPIE_API_CORS_ALLOW_HEADERS", "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id")
	viper.SetDefault("GOPIE_API_CORS_ALLOW_CREDENTIALS", false)
	viper.SetDefault("GOPIE_API_CORS_MAX_AGE", 86400)

	// Flag to determine if CORS is enabled
	viper.SetDefault("GOPIE_CORS_ENABLED", true)
}

func LoadConfig() (*GopieConfig, error) {
	if err := initializeViper(); err != nil {
		return nil, err
	}

	setDefaults()

	config := &GopieConfig{
		Server: ServerConfig{
			Host: viper.GetString("GOPIE_SERVER_HOST"),
			Port: viper.GetString("GOPIE_SERVER_PORT"),
		},
		InternalServer: InternalServerConfig{
			Host: viper.GetString("GOPIE_INTERNAL_SERVER_HOST"),
			Port: viper.GetString("GOPIE_INTERNAL_SERVER_PORT"),
		},
		APIServer: APIServerConfig{
			Host: viper.GetString("GOPIE_API_SERVER_HOST"),
			Port: viper.GetString("GOPIE_API_SERVER_PORT"),
		},
		CORSEnabled: viper.GetBool("GOPIE_CORS_ENABLED"),
		S3: S3Config{
			AccessKey: viper.GetString("GOPIE_S3_ACCESS_KEY"),
			SecretKey: viper.GetString("GOPIE_S3_SECRET_KEY"),
			Region:    viper.GetString("GOPIE_S3_REGION"),
			Endpoint:  viper.GetString("GOPIE_S3_ENDPOINT"),
			SSL:       viper.GetBool("GOPIE_S3_SSL"),
		},
		Logger: LoggerConfig{
			Level:   viper.GetString("GOPIE_LOGGER_LEVEL"),
			LogFile: viper.GetString("GOPIE_LOGGER_FILE"),
			Mode:    viper.GetString("GOPIE_LOGGER_MODE"),
		},
		OlapDB: OlapDBConfig{
			DB:         viper.GetString("GOPIE_OLAPDB_DBTYPE"),
			AccessMode: viper.GetString("GOPIE_OLAPDB_ACCESS_MODE"),
		},
		OpenAI: OpenAIConfig{
			AIModel: viper.GetString("GOPIE_OPENAI_MODEL"),
			Options: viper.GetString("GOPIE_OPENAI_OPTIONS"),
			Apikey:  viper.GetString("GOPIE_OPENAI_APIKEY"),
			BaseUrl: viper.GetString("GOPIE_OPENAI_BASEURL"),
		},
		Meterus: MeterusConfig{
			Addr:   viper.GetString("GOPIE_METERUS_ADDR"),
			ApiKey: viper.GetString("GOPIE_METERUS_APIKEY"),
		},
		Postgres: PostgresConfig{
			Host:     viper.GetString("GOPIE_POSTGRES_HOST"),
			Port:     viper.GetString("GOPIE_POSTGRES_PORT"),
			Database: viper.GetString("GOPIE_POSTGRES_DB"),
			User:     viper.GetString("GOPIE_POSTGRES_USER"),
			Password: viper.GetString("GOPIE_POSTGRES_PASSWORD"),
		},
		Zitadel: ZitadelConfig{
			Protocol:     viper.GetString("GOPIE_ZITADEL_PROTOCOL"),
			Domain:       viper.GetString("GOPIE_ZITADEL_DOMAIN"),
			InsecurePort: viper.GetString("GOPIE_ZITADEL_INSECURE_PORT"),
			ProjectID:    viper.GetString("GOPIE_ZITADEL_PROJECT_ID"),
		},
		EnableZitadel: viper.GetBool("GOPIE_ENABLE_ZITADEL"),
		AIAgent: AIAgentConfig{
			Url: viper.GetString("GOPIE_AIAGENT_URL"),
		},
		DownloadsServer: DownloadsConfig{
			Bucket: viper.GetString("GOPIE_DOWNLOADS_S3_BUCKET"),
		},
		MainCORS: CORSConfig{
			AllowOrigins:     viper.GetString("GOPIE_MAIN_CORS_ALLOW_ORIGINS"),
			AllowMethods:     viper.GetString("GOPIE_MAIN_CORS_ALLOW_METHODS"),
			AllowHeaders:     viper.GetString("GOPIE_MAIN_CORS_ALLOW_HEADERS"),
			AllowCredentials: viper.GetBool("GOPIE_MAIN_CORS_ALLOW_CREDENTIALS"),
			MaxAge:           viper.GetInt("GOPIE_MAIN_CORS_MAX_AGE"),
		},
		InternalCORS: CORSConfig{
			AllowOrigins:     viper.GetString("GOPIE_INTERNAL_CORS_ALLOW_ORIGINS"),
			AllowMethods:     viper.GetString("GOPIE_INTERNAL_CORS_ALLOW_METHODS"),
			AllowHeaders:     viper.GetString("GOPIE_INTERNAL_CORS_ALLOW_HEADERS"),
			AllowCredentials: viper.GetBool("GOPIE_INTERNAL_CORS_ALLOW_CREDENTIALS"),
			MaxAge:           viper.GetInt("GOPIE_INTERNAL_CORS_MAX_AGE"),
		},
		APICORS: CORSConfig{
			AllowOrigins:     viper.GetString("GOPIE_API_CORS_ALLOW_ORIGINS"),
			AllowMethods:     viper.GetString("GOPIE_API_CORS_ALLOW_METHODS"),
			AllowHeaders:     viper.GetString("GOPIE_API_CORS_ALLOW_HEADERS"),
			AllowCredentials: viper.GetBool("GOPIE_API_CORS_ALLOW_CREDENTIALS"),
			MaxAge:           viper.GetInt("GOPIE_API_CORS_MAX_AGE"),
		},
		EncryptionKey: viper.GetString("GOPIE_ENCRYPTION_KEY"),
	}

	var err error
	if config, err = validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}
