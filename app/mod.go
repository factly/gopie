package app

import (
	"github.com/factly/gopie/config"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
)

// App is the main application struct which holds all the global static dependencies
// like logger, config, database, etc
// It is used to pass these dependencies to other packages
type App struct {
	config *config.Config
	logger pkg.Logger
	duckdb *duckdb.Connection
}

func NewApp() *App {
	return &App{}
}

func (a *App) SetConfig(config *config.Config) {
	a.config = config
}

func (a *App) SetDuckDBConnection(duckdb *duckdb.Connection) {
	a.duckdb = duckdb
}

func (a *App) SetLogger(logger pkg.Logger) {
	a.logger = logger
}

func (a *App) GetConfig() *config.Config {
	return a.config
}

func (a *App) GetLogger() *pkg.Logger {
	return &a.logger
}

func (a *App) GetDuckDBConnection() *duckdb.Connection {
	return a.duckdb
}
