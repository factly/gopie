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

func initializeViper() error {
	viper.SetEnvPrefix("gopie")
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

func setDefaults() {
	viper.SetDefault("SERVE_HOST", "localhost")
	viper.SetDefault("SERVE_PORT", "8080")
	viper.SetDefault("S3_REGION", "us-east-1")
	viper.SetDefault("LOGGER_LEVEL", "info")
	viper.SetDefault("LOGGER_FILE", "gopie.log")
	viper.SetDefault("LOGGER_MODE", "dev")
	viper.SetDefault("MOTHERDUCK_ACCESS_MODE", "read_only")
}

func validateConfig(config *GopieConfig) error {
	validations := []struct {
		value string
		name  string
	}{
		{config.S3.AccessKey, "S3 access key"},
		{config.S3.SecretKey, "S3 secret key"},
		{config.S3.Region, "S3 region"},
		{config.MotherDuck.DBName, "MotherDuck DB name"},
		{config.MotherDuck.Token, "MotherDuck token"},
		{config.PortKey.VirtualKey, "portkey virtual key"},
		{config.PortKey.Apikey, "portkey api key"},
		{config.PortKey.BaseUrl, "portkey base url"},
		{config.PortKey.AIModel, "portkey ai model"},
	}

	for _, v := range validations {
		if v.value == "" {
			return fmt.Errorf("missing %s", v.name)
		}
	}
	return nil
}

func LoadConfig() (*GopieConfig, error) {
	if err := initializeViper(); err != nil {
		return nil, err
	}

	setDefaults()

	config := &GopieConfig{
		Serve: ServeConfig{
			Host: viper.GetString("SERVE_HOST"),
			Port: viper.GetString("SERVE_PORT"),
		},
		S3: S3Config{
			AccessKey: viper.GetString("S3_ACCESS_KEY"),
			SecretKey: viper.GetString("S3_SECRET_KEY"),
			Region:    viper.GetString("S3_REGION"),
			Endpoint:  viper.GetString("S3_ENDPOINT"),
		},
		Logger: LoggerConfig{
			Level:   viper.GetString("LOGGER_LEVEL"),
			LogFile: viper.GetString("LOGGER_FILE"),
			Mode:    viper.GetString("LOGGER_MODE"),
		},
		MotherDuck: MotherDuckConfig{
			DBName:     viper.GetString("MOTHERDUCK_DB_NAME"),
			Token:      viper.GetString("MOTHERDUCK_TOKEN"),
			AccessMode: viper.GetString("MOTHERDUCK_ACCESS_MODE"),
		},
		PortKey: PortKeyConfig{
			AIModel:    viper.GetString("PORTKEY_MODEL"),
			VirtualKey: viper.GetString("PORTKEY_VIRTUALKEY"),
			Apikey:     viper.GetString("PORTKEY_APIKEY"),
			BaseUrl:    viper.GetString("PORTKEY_BASEURL"),
		},
		Meterus: MeterusConfig{
			Addr:   viper.GetString("METERUS_ADDR"),
			ApiKey: viper.GetString("METERUS_APIKEY"),
		},
	}

	if err := validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}
