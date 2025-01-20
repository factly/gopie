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
	Serve  ServeConfig
	S3     S3Config
	Logger LoggerConfig
}

func LoadConfig() (*GopieConfig, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("env")
	viper.AddConfigPath(".")

	// Add this line to read the config file
	if err := viper.ReadInConfig(); err != nil {
		log.Fatalf("Error reading config file, %s", err)
		log.Fatalf("Using environment variables")
	}

	fmt.Printf("Using config file: %s\n", viper.ConfigFileUsed())

	fmt.Printf("S3 Access Key: %s\n", viper.GetString("S3_ACCESS_KEY"))
	fmt.Printf("S3 Secret Key: %s\n", viper.GetString("S3_SECRET_KEY"))

	viper.AutomaticEnv()
	// print all the envs with prefix GOPIE

	// Server configuration
	viper.SetDefault("SERVE_HOST", "localhost")
	viper.SetDefault("SERVE_PORT", "8080")

	// S3 configuration
	viper.SetDefault("S3_REGION", "us-east-1")

	// Logger configuration
	viper.SetDefault("LOGGER_LEVEL", "info")
	viper.SetDefault("LOGGER_FILE", "gopie.log")
	viper.SetDefault("LOGGER_MODE", "dev")

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
	}

	// Validate required fields
	if config.S3.AccessKey == "" {
		return nil, fmt.Errorf("missing S3 access key")
	}
	if config.S3.SecretKey == "" {
		return nil, fmt.Errorf("missing S3 secret key")
	}
	if config.S3.Region == "" {
		return nil, fmt.Errorf("missing S3 region")
	}

	return config, nil
}
