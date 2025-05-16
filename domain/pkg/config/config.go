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

type GopieConfig struct {
	Server   ServerConfig
	S3       S3Config
	Logger   LoggerConfig
	OlapDB   OlapDBConfig
	PortKey  PortKeyConfig
	Meterus  MeterusConfig
	Postgres PostgresConfig
	Zitadel  ZitadelConfig
	AIAgent  AIAgentConfig
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
	DBName string
	Token  string
}

type PortKeyConfig struct {
	VirtualKey string
	Apikey     string
	BaseUrl    string
	AIModel    string
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

type ZitadelConfig struct {
	Protocol            string
	Domain              string
	InsecurePort        string
	ProjectID           string
	PersonalAccessToken string
	ServiceUserID       string
	LoginURL            string
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
		{config.PortKey.VirtualKey, "portkey virtual key"},
		{config.PortKey.Apikey, "portkey api key"},
		{config.PortKey.BaseUrl, "portkey base url"},
		{config.PortKey.AIModel, "portkey ai model"},
		{config.Postgres.Host, "postgres host"},
		{config.Postgres.Port, "postgres port"},
		{config.Postgres.Database, "postgres database"},
		{config.Postgres.User, "postgres user"},
		{config.Postgres.Password, "postgres password"},
		{config.AIAgent.Url, "ai agent url"},
		// {config.Zitadel.Protocol, "zitadel protocol"},
		// {config.Zitadel.Domain, "zitadel domain"},
		// {config.Zitadel.ProjectID, "zitadel project id"},
		// {config.Zitadel.PersonalAccessToken, "zitadel personal access token"},
		// {config.Zitadel.ServiceUserID, "zitadel service user id"},
		// {config.Zitadel.LoginURL, "zitadel app login url"},
	}

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
			DBName: viper.GetString("GOPIE_MOTHERDUCK_DB_NAME"),
			Token:  viper.GetString("GOPIE_MOTHERDUCK_TOKEN"),
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
	viper.SetDefault("GOPIE_S3_REGION", "us-east-1")
	viper.SetDefault("GOPIE_S3_SSL", false)
	viper.SetDefault("GOPIE_LOGGER_LEVEL", "info")
	viper.SetDefault("GOPIE_LOGGER_FILE", "gopie.log")
	viper.SetDefault("GOPIE_LOGGER_MODE", "dev")
	viper.SetDefault("GOPIE_OLAPDB_ACCESS_MODE", "read_write")
	viper.SetDefault("GOPIE_DUCKDB_CPU", 1)
	viper.SetDefault("GOPIE_DUCKDB_MEMORY_LIMIT", 1024)
	viper.SetDefault("GOPIE_DUCKDB_STORAGE_LIMIT", 1024)
	viper.SetDefault("GOPIE_DUCKDB_PATH", "./duckdb/gopie.db")
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
		PortKey: PortKeyConfig{
			AIModel:    viper.GetString("GOPIE_PORTKEY_MODEL"),
			VirtualKey: viper.GetString("GOPIE_PORTKEY_VIRTUALKEY"),
			Apikey:     viper.GetString("GOPIE_PORTKEY_APIKEY"),
			BaseUrl:    viper.GetString("GOPIE_PORTKEY_BASEURL"),
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
			Protocol:            viper.GetString("GOPIE_ZITADEL_PROTOCOL"),
			Domain:              viper.GetString("GOPIE_ZITADEL_DOMAIN"),
			InsecurePort:        viper.GetString("GOPIE_ZITADEL_INSECURE_PORT"),
			ProjectID:           viper.GetString("GOPIE_ZITADEL_PROJECT_ID"),
			PersonalAccessToken: viper.GetString("GOPIE_ZITADEL_PERSONAL_ACCESS_TOKEN"),
			ServiceUserID:       viper.GetString("GOPIE_ZITADEL_SERVICE_USER_ID"),
			LoginURL:            viper.GetString("GOPIE_ZITADEL_APP_LOGIN_URL"),
		},
		AIAgent: AIAgentConfig{
			Url: viper.GetString("GOPIE_AIAGENT_URL"),
		},
	}
	fmt.Println("===>>> ", viper.GetString("GOPIE_AIAGENT_URL"))

	var err error
	if config, err = validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}
