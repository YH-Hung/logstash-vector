package report

import (
	"fmt"
	"os"
	"strings"

	"github.com/yourusername/lv-go/internal/models"
)

// WriteReport writes a migration report to a file
func WriteReport(report *models.MigrationReport, outputPath string) error {
	content := report.ToMarkdown()
	return os.WriteFile(outputPath, []byte(content), 0644)
}

// WriteCombinedReport writes a combined report for multiple migrations
func WriteCombinedReport(reports []models.MigrationReport, outputPath string) error {
	var sb strings.Builder

	sb.WriteString("# Combined Migration Report\n\n")
	sb.WriteString(fmt.Sprintf("**Total Files Migrated:** %d\n\n", len(reports)))

	// Overall statistics
	totalSupported := 0
	totalUnsupported := 0
	totalErrors := 0

	for _, report := range reports {
		totalSupported += len(report.SupportedPlugins)
		totalUnsupported += len(report.UnsupportedPlugins)
		totalErrors += len(report.Errors)
	}

	sb.WriteString("## Overall Statistics\n")
	sb.WriteString(fmt.Sprintf("- ✅ Successfully migrated plugins: %d\n", totalSupported))
	sb.WriteString(fmt.Sprintf("- ⚠️  Unsupported plugins: %d\n", totalUnsupported))
	sb.WriteString(fmt.Sprintf("- ❌ Total errors: %d\n\n", totalErrors))

	// Individual file reports
	sb.WriteString("## Individual File Reports\n\n")

	for i, report := range reports {
		sb.WriteString(fmt.Sprintf("### %d. %s\n\n", i+1, report.SourceFile))
		sb.WriteString(fmt.Sprintf("**Target:** `%s`\n", report.TargetFile))
		sb.WriteString(fmt.Sprintf("**Success Rate:** %.1f%%\n", report.SuccessRate()))
		sb.WriteString(fmt.Sprintf("- Supported: %d\n", len(report.SupportedPlugins)))
		sb.WriteString(fmt.Sprintf("- Unsupported: %d\n", len(report.UnsupportedPlugins)))
		sb.WriteString(fmt.Sprintf("- Errors: %d\n\n", len(report.Errors)))

		// Show unsupported plugins if any
		if len(report.UnsupportedPlugins) > 0 {
			sb.WriteString("**Unsupported Plugins:**\n")
			for _, plugin := range report.UnsupportedPlugins {
				sb.WriteString(fmt.Sprintf("- %s (%s) at line %d\n", plugin.PluginName, plugin.PluginType, plugin.LineNumber))
			}
			sb.WriteString("\n")
		}

		// Show errors if any
		if len(report.Errors) > 0 {
			sb.WriteString("**Errors:**\n")
			for _, err := range report.Errors {
				sb.WriteString(fmt.Sprintf("- %s\n", err.Error()))
			}
			sb.WriteString("\n")
		}

		sb.WriteString("---\n\n")
	}

	// Detailed reports
	sb.WriteString("## Detailed Reports\n\n")
	for i, report := range reports {
		sb.WriteString(fmt.Sprintf("### File %d: %s\n\n", i+1, report.SourceFile))
		sb.WriteString(report.ToMarkdown())
		sb.WriteString("\n---\n\n")
	}

	return os.WriteFile(outputPath, []byte(sb.String()), 0644)
}
