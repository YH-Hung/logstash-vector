package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

const version = "0.1.0"

var rootCmd = &cobra.Command{
	Use:   "lv-go",
	Short: "Logstash to Vector migration tool",
	Long: `lv-go is a command-line tool for migrating Logstash configurations to Vector format.
It supports automatic transformation of common Logstash plugins to their Vector equivalents,
with detailed migration reports for unsupported plugins.`,
	Version: version,
}

// Execute runs the CLI
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.AddCommand(migrateCmd)
	rootCmd.AddCommand(validateCmd)
	rootCmd.AddCommand(diffCmd)
}
