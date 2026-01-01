package cli

import (
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/yourusername/lv-go/internal/models"
	"github.com/yourusername/lv-go/internal/parser"
)

var diffCmd = &cobra.Command{
	Use:   "diff <logstash.conf> <vector.toml>",
	Short: "Show side-by-side comparison of Logstash and Vector configs",
	Long: `Display a comparison between a Logstash configuration and its migrated Vector equivalent.
Shows the mapping of inputs→sources, filters→transforms, and outputs→sinks.`,
	Args: cobra.ExactArgs(2),
	RunE: runDiff,
}

func runDiff(cmd *cobra.Command, args []string) error {
	logstashFile := args[0]
	vectorFile := args[1]

	// Verify files exist
	if _, err := os.Stat(logstashFile); err != nil {
		return fmt.Errorf("logstash file not found: %s", logstashFile)
	}
	if _, err := os.Stat(vectorFile); err != nil {
		return fmt.Errorf("vector file not found: %s", vectorFile)
	}

	// Parse Logstash config
	logstashConfig, err := parser.ParseFile(logstashFile)
	if err != nil {
		return fmt.Errorf("failed to parse Logstash config: %w", err)
	}

	// Print header
	color.Cyan("Configuration Comparison\n")
	color.Cyan("========================\n\n")

	fmt.Printf("Logstash: %s\n", logstashFile)
	fmt.Printf("Vector:   %s\n\n", vectorFile)

	// Show inputs → sources mapping
	if len(logstashConfig.Inputs) > 0 {
		color.Yellow("Inputs → Sources\n")
		color.Yellow("----------------\n")
		for i, input := range logstashConfig.Inputs {
			componentType := getComponentType(models.PluginTypeInput, input.PluginName)
			fmt.Printf("%d. %s (input) → %s (source)\n", i+1, input.PluginName, componentType)
			if verbose {
				printPluginConfig(input.Config)
			}
		}
		fmt.Println()
	}

	// Show filters → transforms mapping
	if len(logstashConfig.Filters) > 0 {
		color.Yellow("Filters → Transforms\n")
		color.Yellow("--------------------\n")
		for i, filter := range logstashConfig.Filters {
			componentType := getComponentType(models.PluginTypeFilter, filter.PluginName)
			fmt.Printf("%d. %s (filter) → %s (transform)\n", i+1, filter.PluginName, componentType)
			if verbose {
				printPluginConfig(filter.Config)
			}
		}
		fmt.Println()
	}

	// Show outputs → sinks mapping
	if len(logstashConfig.Outputs) > 0 {
		color.Yellow("Outputs → Sinks\n")
		color.Yellow("---------------\n")
		for i, output := range logstashConfig.Outputs {
			componentType := getComponentType(models.PluginTypeOutput, output.PluginName)
			fmt.Printf("%d. %s (output) → %s (sink)\n", i+1, output.PluginName, componentType)
			if verbose {
				printPluginConfig(output.Config)
			}
		}
		fmt.Println()
	}

	return nil
}

func getComponentType(pluginType models.PluginType, pluginName string) string {
	// Map known plugins to their Vector equivalents
	switch pluginType {
	case models.PluginTypeInput:
		switch pluginName {
		case "file":
			return "file"
		case "beats":
			return "socket"
		default:
			return "unknown"
		}
	case models.PluginTypeFilter:
		switch pluginName {
		case "grok", "mutate", "date":
			return "remap"
		default:
			return "unknown"
		}
	case models.PluginTypeOutput:
		switch pluginName {
		case "elasticsearch":
			return "elasticsearch"
		case "file":
			return "file"
		default:
			return "unknown"
		}
	}
	return "unknown"
}

func printPluginConfig(config map[string]interface{}) {
	for key, value := range config {
		fmt.Printf("    %s => %v\n", key, value)
	}
}
