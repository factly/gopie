package cmd

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
	Use:   "downloads-server",
	Short: "downloads server",
}

func Execute() {
	cobra.CheckErr(rootCmd.Execute())
}
