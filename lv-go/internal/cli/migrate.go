package cli

import (
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/yourusername/lv-go/internal/models"
	"github.com/yourusername/lv-go/pkg/api"
)

var (
	dryRun     bool
	outputDir  string
	reportPath string
	doValidate bool
	verbose    bool
	quiet      bool
	overwrite  bool
)

var migrateCmd = &cobra.Command{
	Use:   "migrate <directory>",
	Short: "Migrate Logstash configurations to Vector format",
	Long: `Migrate all .conf files in a directory to Vector .toml format.
Supports dry-run mode, custom output directories, and automatic validation.`,
	Args: cobra.ExactArgs(1),
	RunE: runMigrate,
}

func init() {
	migrateCmd.Flags().BoolVarP(&dryRun, "dry-run", "n", false, "Preview migration without writing files")
	migrateCmd.Flags().StringVarP(&outputDir, "output-dir", "o", "", "Custom output directory (default: same as input)")
	migrateCmd.Flags().StringVarP(&reportPath, "report", "r", "", "Custom migration report path")
	migrateCmd.Flags().BoolVar(&doValidate, "validate", true, "Validate generated Vector configs")
	migrateCmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "Verbose output")
	migrateCmd.Flags().BoolVarP(&quiet, "quiet", "q", false, "Minimal output")
	migrateCmd.Flags().BoolVarP(&overwrite, "overwrite", "f", false, "Overwrite existing files without confirmation")
}

func runMigrate(cmd *cobra.Command, args []string) error {
	directory := args[0]

	// Verify directory exists
	if info, err := os.Stat(directory); err != nil || !info.IsDir() {
		return fmt.Errorf("directory not found or not accessible: %s", directory)
	}

	// Print header
	if !quiet {
		color.Cyan("Migrating Logstash configurations from: %s\n", directory)
		if dryRun {
			color.Yellow("DRY RUN MODE - No files will be written\n")
		}
		fmt.Println()
	}

	// Run migration
	result, err := api.MigrateDirectory(directory, outputDir, dryRun, doValidate)
	if err != nil {
		return err
	}

	// Print results
	if !quiet {
		printMigrationResults(result)
	}

	// Return exit code 1 if any files failed
	if result.FailureCount > 0 {
		return fmt.Errorf("migration completed with %d failures", result.FailureCount)
	}

	return nil
}

func printMigrationResults(result *models.MigrationResult) {
	fmt.Println("Migration Results:")
	fmt.Println("==================")
	fmt.Printf("Total files: %d\n", result.TotalFiles)

	// Success count
	if result.SuccessCount > 0 {
		color.Green("✓ Successfully migrated: %d\n", result.SuccessCount)
	}

	// Failure count
	if result.FailureCount > 0 {
		color.Red("✗ Failed: %d\n", result.FailureCount)
	}

	fmt.Println()

	// Per-file summary
	if verbose {
		for i, report := range result.Reports {
			fmt.Printf("%d. %s\n", i+1, report.SourceFile)
			fmt.Printf("   Target: %s\n", report.TargetFile)
			fmt.Printf("   Success rate: %.1f%%\n", report.SuccessRate())
			fmt.Printf("   Supported: %d, Unsupported: %d, Errors: %d\n",
				len(report.SupportedPlugins),
				len(report.UnsupportedPlugins),
				len(report.Errors))

			if len(report.Errors) > 0 {
				color.Red("   Errors:\n")
				for _, err := range report.Errors {
					fmt.Printf("     - %s\n", err.Error())
				}
			}

			fmt.Println()
		}
	}

	// Summary statistics
	totalSupported := 0
	totalUnsupported := 0
	totalErrors := 0

	for _, report := range result.Reports {
		totalSupported += len(report.SupportedPlugins)
		totalUnsupported += len(report.UnsupportedPlugins)
		totalErrors += len(report.Errors)
	}

	fmt.Println("Plugin Summary:")
	color.Green("  ✓ Supported plugins: %d\n", totalSupported)
	if totalUnsupported > 0 {
		color.Yellow("  ⚠ Unsupported plugins: %d (manual migration required)\n", totalUnsupported)
	}
	if totalErrors > 0 {
		color.Red("  ✗ Errors: %d\n", totalErrors)
	}

	fmt.Println()
	color.Cyan("See migration-report.md for detailed information\n")
}
