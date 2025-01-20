package logger

import (
	"fmt"

	"github.com/mitchellh/mapstructure"
	"go.uber.org/zap"
)

type LogLevel string

const (
	INFO     LogLevel = "info"
	WARN     LogLevel = "warn"
	CRITICAL LogLevel = "critical"
	ERROR    LogLevel = "error"
)

type loggerConfig struct {
	LogLevel LogLevel `mapstructure:"log_level"`
	LogFile  string   `mapstructure:"log_file"`
	Mode     string   `mapstructure:"mode"`
}

type Logger struct {
	*zap.Logger
}

func parseLoggerConfig(properties map[string]any) (*loggerConfig, error) {
	config := &loggerConfig{
		LogLevel: INFO,
		Mode:     "dev",
	}

	if err := mapstructure.Decode(properties, config); err != nil {
		return nil, fmt.Errorf("failed to parse logger config: %w", err)
	}

	return config, nil
}

func NewLogger(properties map[string]any) (*Logger, error) {
	config, err := parseLoggerConfig(properties)
	if err != nil {
		return nil, err
	}

	var logger *zap.Logger
	var zapConfig zap.Config
	if config.Mode == "dev" {
		zapConfig = zap.NewDevelopmentConfig()
	} else {
		zapConfig = zap.NewProductionConfig()
	}

	zapConfig.Level = zap.NewAtomicLevelAt(zap.DebugLevel)
	zapConfig.OutputPaths = []string{config.LogFile}

	logger, err = zapConfig.Build()
	if err != nil {
		return nil, fmt.Errorf("failed to create logger: %w", err)
	}

	return &Logger{logger}, nil
}
