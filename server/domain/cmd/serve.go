package cmd

import (
	"log"

	"github.com/factly/gopie/interfaces/http"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(serveCmd)
}

var serveCmd = &cobra.Command{
	Use:   "serve",
	Short: "Start HTTP server",
	Run: func(cmd *cobra.Command, args []string) {
		// Call the ServeHttp function from the http package
		if err := http.ServeHttp(); err != nil {
			log.Fatal(err)
		}
	},
}
