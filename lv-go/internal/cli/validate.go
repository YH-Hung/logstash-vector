package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/yourusername/lv-go/internal/validator"
)

var validateCmd = &cobra.Command{
	Use:   "validate [files...]",
	Short: "Validate Vector TOML configuration files",
	Long: `Validate Vector TOML files using the 'vector validate' command.
If no files are specified, validates all .toml files in the current directory.`,
	RunE: runValidate,
}

func runValidate(cmd *cobra.Command, args []string) error {
	var files []string

	// If no files specified, find all .toml files in current directory
	if len(args) == 0 {
		matches, err := filepath.Glob("*.toml")
		if err != nil {
			return fmt.Errorf("failed to find .toml files: %w", err)
		}
		files = matches
	} else {
		files = args
	}

	if len(files) == 0 {
		return fmt.Errorf("no .toml files found to validate")
	}

	// Validate each file
	allValid := true
	for _, file := range files {
		// Check if file exists
		if _, err := os.Stat(file); err != nil {
			color.Red("✗ %s: file not found\n", file)
			allValid = false
			continue
		}

		// Validate
		isValid, output, err := validator.ValidateVectorConfig(file)
		if err != nil {
			color.Red("✗ %s: validation error: %v\n", file, err)
			allValid = false
			continue
		}

		if isValid {
			color.Green("✓ %s: valid\n", file)
		} else {
			color.Red("✗ %s: invalid\n", file)
			if verbose {
				fmt.Println(output)
			}
			allValid = false
		}
	}

	if !allValid {
		return fmt.Errorf("some files failed validation")
	}

	fmt.Println()
	color.Green("All files are valid!\n")
	return nil
}
