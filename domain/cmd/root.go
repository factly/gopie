package cmd

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
	Use:   "gopie",
	Short: "gopie is a query engine for tabular datafiles",
}

func Execute() {
	cobra.CheckErr(rootCmd.Execute())
}
