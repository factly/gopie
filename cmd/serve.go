package cmd

import (
	"github.com/factly/gopie/api"
	"github.com/factly/gopie/app"
	"github.com/factly/gopie/config"
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
	configService, err := config.LoadConfig()
	if err != nil {
		return
	}

	logger := pkg.NewLogger()
	err = logger.SetConfig(&configService.Logger)
	if err != nil {
		logger.Fatal("error setting logger config", "err", err.Error())
	}

	app := app.NewApp()
	app.SetConfig(configService)
	app.SetLogger(*logger)

	api.RunHttpServer(app)
}
