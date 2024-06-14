package cmd

import (
	"fmt"

	"github.com/factly/gopie/app"
	"github.com/factly/gopie/config"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/http"
	"github.com/factly/gopie/pkg"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(serveCmd)
}

var serveCmd = &cobra.Command{
	Use:   "serve",
	Short: "Start gopie server.",
	Run: func(cmd *cobra.Command, args []string) {
		serve()
	},
}

// setup and go-chi server
func serve() {
	config := config.New()
	cfg, err := config.LoadConfig()
	if err != nil {
		return
	}

	logger := pkg.NewLogger()
	err = logger.SetConfig(&cfg.Logger)
	if err != nil {
		logger.Fatal("error setting logger config", "err", err.Error())
	}

	// create duckdb connnection
	driver := duckdb.Driver{}
	// set additional config for duckdb

	duckDbCfg := cfg.DuckDB
	duckDbCfg["external_table_storage"] = true
	duckDbCfg["allow_host_access"] = true
	conn, err := driver.Open(duckDbCfg, logger)
	if err != nil {
		logger.Fatal(fmt.Sprintf("Error creating duckdb connection: %s", err.Error()))
	}

	app := app.NewApp()
	app.SetConfig(cfg)
	app.SetLogger(*logger)
	app.SetDuckDBConnection(conn)

	http.RunHttpServer(app)
}
