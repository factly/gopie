package cmd

import (
	"log"

	"github.com/factly/gopie/downlods-server/server"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(serveCmd)
}

var serveCmd = &cobra.Command{
	Use:   "serve",
	Short: "Start HTTP server",
	Run: func(cmd *cobra.Command, args []string) {
		if err := server.ServeHttp(); err != nil {
			log.Fatal(err)
		}
	},
}
