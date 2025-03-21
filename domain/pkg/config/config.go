package config

import (
	"fmt"
	"log"

	"github.com/spf13/viper"
)

type ServeConfig struct {
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
}

type LoggerConfig struct {
	Level   string
	LogFile string
	Mode    string
}

type GopieConfig struct {
	Serve      ServeConfig
	S3         S3Config
	Logger     LoggerConfig
	MotherDuck MotherDuckConfig
	PortKey    PortKeyConfig
	Meterus    MeterusConfig
	Postgres   PostgresConfig
}

type MotherDuckConfig struct {
	DBName     string
	Token      string
	AccessMode string
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

func validateConfig(config *GopieConfig) error {
	validations := []struct {
		value string
		name  string
	}{
		{config.MotherDuck.DBName, "MotherDuck DB name"},
		{config.MotherDuck.Token, "MotherDuck token"},
		{config.PortKey.VirtualKey, "portkey virtual key"},
		{config.PortKey.Apikey, "portkey api key"},
		{config.PortKey.BaseUrl, "portkey base url"},
		{config.PortKey.AIModel, "portkey ai model"},
		{config.Postgres.Host, "postgres host"},
		{config.Postgres.Port, "postgres port"},
		{config.Postgres.Database, "postgres database"},
		{config.Postgres.User, "postgres user"},
		{config.Postgres.Password, "postgres password"},
	}

	for _, v := range validations {
		if v.value == "" {
			return fmt.Errorf("missing %s", v.name)
		}
	}
	return nil
}

func setDefaults() {
	viper.SetDefault("GOPIE_SERVE_HOST", "localhost")
	viper.SetDefault("GOPIE_SERVE_PORT", "8080")
	viper.SetDefault("GOPIE_S3_REGION", "us-east-1")
	viper.SetDefault("GOPIE_LOGGER_LEVEL", "info")
	viper.SetDefault("GOPIE_LOGGER_FILE", "gopie.log")
	viper.SetDefault("GOPIE_LOGGER_MODE", "dev")
	viper.SetDefault("GOPIE_MOTHERDUCK_ACCESS_MODE", "read_only")
}

func LoadConfig() (*GopieConfig, error) {
	if err := initializeViper(); err != nil {
		return nil, err
	}

	setDefaults()

	config := &GopieConfig{
		Serve: ServeConfig{
			Host: viper.GetString("GOPIE_SERVE_HOST"),
			Port: viper.GetString("GOPIE_SERVE_PORT"),
		},
		S3: S3Config{
			AccessKey: viper.GetString("GOPIE_S3_ACCESS_KEY"),
			SecretKey: viper.GetString("GOPIE_S3_SECRET_KEY"),
			Region:    viper.GetString("GOPIE_S3_REGION"),
			Endpoint:  viper.GetString("GOPIE_S3_ENDPOINT"),
		},
		Logger: LoggerConfig{
			Level:   viper.GetString("GOPIE_LOGGER_LEVEL"),
			LogFile: viper.GetString("GOPIE_LOGGER_FILE"),
			Mode:    viper.GetString("GOPIE_LOGGER_MODE"),
		},
		MotherDuck: MotherDuckConfig{
			DBName:     viper.GetString("GOPIE_MOTHERDUCK_DB_NAME"),
			Token:      viper.GetString("GOPIE_MOTHERDUCK_TOKEN"),
			AccessMode: viper.GetString("GOPIE_MOTHERDUCK_ACCESS_MODE"),
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
	}

	if err := validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}
