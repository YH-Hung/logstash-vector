package models

import (
	"fmt"
	"strings"
	"time"
)

// MigrationError represents an error that occurred during migration
type MigrationError struct {
	ErrorType  ErrorType
	Message    string
	LineNumber int
	FilePath   string
}

func (e *MigrationError) Error() string {
	if e.LineNumber > 0 {
		return fmt.Sprintf("%s:%d: %s", e.FilePath, e.LineNumber, e.Message)
	}
	return fmt.Sprintf("%s: %s", e.FilePath, e.Message)
}

// PluginMigration represents a successfully migrated plugin
type PluginMigration struct {
	PluginName       string
	PluginType       PluginType
	VectorComponents []string
	Notes            string
}

// UnsupportedPlugin represents a plugin that couldn't be automatically migrated
type UnsupportedPlugin struct {
	PluginName                string
	PluginType                PluginType
	LineNumber                int
	OriginalConfig            string
	ManualMigrationGuidance   string
	VectorAlternatives        []string
}

// MigrationReport represents the results of migrating a single configuration file
type MigrationReport struct {
	SourceFile         string
	TargetFile         string
	Timestamp          time.Time
	SupportedPlugins   []PluginMigration
	UnsupportedPlugins []UnsupportedPlugin
	Errors             []MigrationError
	Warnings           []string
}

// SuccessRate calculates the percentage of successfully migrated plugins
func (mr *MigrationReport) SuccessRate() float64 {
	total := len(mr.SupportedPlugins) + len(mr.UnsupportedPlugins)
	if total == 0 {
		return 0.0
	}
	return float64(len(mr.SupportedPlugins)) / float64(total) * 100.0
}

// ToMarkdown generates a markdown representation of the migration report
func (mr *MigrationReport) ToMarkdown() string {
	var sb strings.Builder

	sb.WriteString("# Migration Report\n\n")
	sb.WriteString(fmt.Sprintf("**Source:** `%s`\n", mr.SourceFile))
	sb.WriteString(fmt.Sprintf("**Target:** `%s`\n", mr.TargetFile))
	sb.WriteString(fmt.Sprintf("**Generated:** %s\n", mr.Timestamp.Format("2006-01-02T15:04:05")))
	sb.WriteString(fmt.Sprintf("**Success Rate:** %.1f%%\n\n", mr.SuccessRate()))

	// Summary
	sb.WriteString("## Summary\n")
	sb.WriteString(fmt.Sprintf("- ✅ Successfully migrated: %d plugins\n", len(mr.SupportedPlugins)))
	sb.WriteString(fmt.Sprintf("- ⚠️  Unsupported plugins: %d\n", len(mr.UnsupportedPlugins)))
	sb.WriteString(fmt.Sprintf("- ❌ Errors: %d\n\n", len(mr.Errors)))

	// Successfully migrated plugins
	if len(mr.SupportedPlugins) > 0 {
		sb.WriteString("## Successfully Migrated Plugins\n\n")
		for _, plugin := range mr.SupportedPlugins {
			sb.WriteString(fmt.Sprintf("### %s (%s)\n", plugin.PluginName, plugin.PluginType))
			sb.WriteString(fmt.Sprintf("- **Vector components:** %s\n", strings.Join(plugin.VectorComponents, ", ")))
			if plugin.Notes != "" {
				sb.WriteString(fmt.Sprintf("- **Notes:** %s\n", plugin.Notes))
			}
			sb.WriteString("\n")
		}
	}

	// Unsupported plugins
	if len(mr.UnsupportedPlugins) > 0 {
		sb.WriteString("## Unsupported Plugins (Manual Migration Required)\n\n")
		for _, plugin := range mr.UnsupportedPlugins {
			sb.WriteString(fmt.Sprintf("### %s (line %d)\n", plugin.PluginName, plugin.LineNumber))
			sb.WriteString(fmt.Sprintf("- **Type:** %s\n\n", plugin.PluginType))

			if plugin.OriginalConfig != "" {
				sb.WriteString("**Original Configuration:**\n```\n")
				sb.WriteString(plugin.OriginalConfig)
				sb.WriteString("\n```\n\n")
			}

			if plugin.ManualMigrationGuidance != "" {
				sb.WriteString("**Migration Guidance:**\n")
				sb.WriteString(plugin.ManualMigrationGuidance)
				sb.WriteString("\n\n")
			}

			if len(plugin.VectorAlternatives) > 0 {
				sb.WriteString("**Vector Alternatives:**\n")
				for _, alt := range plugin.VectorAlternatives {
					sb.WriteString(fmt.Sprintf("- %s\n", alt))
				}
				sb.WriteString("\n")
			}
		}
	}

	// Errors
	if len(mr.Errors) > 0 {
		sb.WriteString("## Errors\n\n")
		for _, err := range mr.Errors {
			sb.WriteString(fmt.Sprintf("- **%s:** %s\n", err.ErrorType, err.Error()))
		}
		sb.WriteString("\n")
	}

	// Warnings
	if len(mr.Warnings) > 0 {
		sb.WriteString("## Warnings\n\n")
		for _, warning := range mr.Warnings {
			sb.WriteString(fmt.Sprintf("- %s\n", warning))
		}
		sb.WriteString("\n")
	}

	return sb.String()
}

// MigrationResult represents the aggregated results of migrating multiple files
type MigrationResult struct {
	Reports      []MigrationReport
	TotalFiles   int
	SuccessCount int
	FailureCount int
}

// AddReport adds a migration report to the result
func (mr *MigrationResult) AddReport(report MigrationReport) {
	mr.Reports = append(mr.Reports, report)
	mr.TotalFiles++
	if len(report.Errors) == 0 {
		mr.SuccessCount++
	} else {
		mr.FailureCount++
	}
}
