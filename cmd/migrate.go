package cmd

import (
	"context"
	"fmt"
	"log"

	"github.com/factly/gopie/config"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(migrateCmd)
}

var migrateCmd = &cobra.Command{
	Use:   "migrate",
	Short: "Run duckdb migrations for gopie",
	Run: func(cmd *cobra.Command, args []string) {
		migrate()
	},
}

func migrate() {
	config := config.New()
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("error loading config: ", err.Error())
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

	err = conn.Migrate(context.Background())
	if err != nil {
		return
	}
	logger.Info("success..")
}
