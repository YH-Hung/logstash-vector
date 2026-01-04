package models

import (
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestMigrationError_Error(t *testing.T) {
	t.Run("formats error with line number", func(t *testing.T) {
		err := &MigrationError{
			ErrorType:  ErrorTypeParseError,
			Message:    "Invalid syntax",
			LineNumber: 42,
			FilePath:   "/path/to/file.conf",
		}

		result := err.Error()

		assert.Equal(t, "/path/to/file.conf:42: Invalid syntax", result)
	})

	t.Run("formats error without line number", func(t *testing.T) {
		err := &MigrationError{
			ErrorType:  ErrorTypeValidationError,
			Message:    "Missing required field",
			LineNumber: 0, // No line number
			FilePath:   "/path/to/file.conf",
		}

		result := err.Error()

		assert.Equal(t, "/path/to/file.conf: Missing required field", result)
	})

	t.Run("handles negative line number", func(t *testing.T) {
		err := &MigrationError{
			ErrorType:  ErrorTypeParseError,
			Message:    "Test error",
			LineNumber: -1,
			FilePath:   "test.conf",
		}

		result := err.Error()

		// Negative line number should be treated as no line number
		assert.Equal(t, "test.conf: Test error", result)
	})
}

func TestMigrationReport_SuccessRate(t *testing.T) {
	t.Run("returns 100% for all supported plugins", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins: []PluginMigration{
				{PluginName: "file", PluginType: PluginTypeInput},
				{PluginName: "grok", PluginType: PluginTypeFilter},
				{PluginName: "elasticsearch", PluginType: PluginTypeOutput},
			},
			UnsupportedPlugins: []UnsupportedPlugin{},
		}

		rate := report.SuccessRate()

		assert.Equal(t, 100.0, rate)
	})

	t.Run("returns 0% for all unsupported plugins", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins: []PluginMigration{},
			UnsupportedPlugins: []UnsupportedPlugin{
				{PluginName: "kafka", PluginType: PluginTypeInput},
				{PluginName: "ruby", PluginType: PluginTypeFilter},
			},
		}

		rate := report.SuccessRate()

		assert.Equal(t, 0.0, rate)
	})

	t.Run("returns 0% for zero plugins", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins:   []PluginMigration{},
			UnsupportedPlugins: []UnsupportedPlugin{},
		}

		rate := report.SuccessRate()

		assert.Equal(t, 0.0, rate)
	})

	t.Run("calculates correct percentage for mixed plugins", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins: []PluginMigration{
				{PluginName: "file"},
				{PluginName: "grok"},
			},
			UnsupportedPlugins: []UnsupportedPlugin{
				{PluginName: "kafka"},
			},
		}

		rate := report.SuccessRate()

		// 2 supported out of 3 total = 66.666...%
		assert.InDelta(t, 66.67, rate, 0.01)
	})

	t.Run("calculates 50% success rate", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins: []PluginMigration{
				{PluginName: "file"},
			},
			UnsupportedPlugins: []UnsupportedPlugin{
				{PluginName: "kafka"},
			},
		}

		rate := report.SuccessRate()

		assert.Equal(t, 50.0, rate)
	})

	t.Run("handles many plugins", func(t *testing.T) {
		report := &MigrationReport{
			SupportedPlugins: make([]PluginMigration, 90),
			UnsupportedPlugins: make([]UnsupportedPlugin, 10),
		}

		rate := report.SuccessRate()

		// 90 out of 100 = 90%
		assert.Equal(t, 90.0, rate)
	})
}

func TestMigrationReport_ToMarkdown(t *testing.T) {
	t.Run("generates complete markdown report", func(t *testing.T) {
		timestamp := time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC)
		report := &MigrationReport{
			SourceFile: "/path/to/input.conf",
			TargetFile: "/path/to/output.toml",
			Timestamp:  timestamp,
			SupportedPlugins: []PluginMigration{
				{
					PluginName:       "file",
					PluginType:       PluginTypeInput,
					VectorComponents: []string{"file_source_0"},
					Notes:            "Successfully migrated",
				},
			},
			UnsupportedPlugins: []UnsupportedPlugin{
				{
					PluginName:              "kafka",
					PluginType:              PluginTypeInput,
					LineNumber:              10,
					OriginalConfig:          "kafka { bootstrap_servers => \"localhost:9092\" }",
					ManualMigrationGuidance: "Use Vector kafka source",
					VectorAlternatives:      []string{"kafka source", "http source"},
				},
			},
			Errors: []MigrationError{
				{
					ErrorType:  ErrorTypeParseError,
					Message:    "Invalid syntax",
					LineNumber: 5,
					FilePath:   "/path/to/input.conf",
				},
			},
			Warnings: []string{"Missing field defaults applied"},
		}

		markdown := report.ToMarkdown()

		// Verify key sections are present
		assert.Contains(t, markdown, "# Migration Report")
		assert.Contains(t, markdown, "**Source:** `/path/to/input.conf`")
		assert.Contains(t, markdown, "**Target:** `/path/to/output.toml`")
		assert.Contains(t, markdown, "2024-01-01T12:00:00")
		assert.Contains(t, markdown, "## Summary")
		assert.Contains(t, markdown, "✅ Successfully migrated: 1 plugins")
		assert.Contains(t, markdown, "⚠️  Unsupported plugins: 1")
		assert.Contains(t, markdown, "❌ Errors: 1")
		assert.Contains(t, markdown, "## Successfully Migrated Plugins")
		assert.Contains(t, markdown, "file (input)")
		assert.Contains(t, markdown, "file_source_0")
		assert.Contains(t, markdown, "Successfully migrated")
		assert.Contains(t, markdown, "## Unsupported Plugins")
		assert.Contains(t, markdown, "kafka (line 10)")
		assert.Contains(t, markdown, "Use Vector kafka source")
		assert.Contains(t, markdown, "kafka source")
		assert.Contains(t, markdown, "## Errors")
		assert.Contains(t, markdown, "parse_error")
		assert.Contains(t, markdown, "## Warnings")
		assert.Contains(t, markdown, "Missing field defaults applied")
	})

	t.Run("handles empty report", func(t *testing.T) {
		report := &MigrationReport{
			SourceFile:         "input.conf",
			TargetFile:         "output.toml",
			Timestamp:          time.Now(),
			SupportedPlugins:   []PluginMigration{},
			UnsupportedPlugins: []UnsupportedPlugin{},
			Errors:             []MigrationError{},
			Warnings:           []string{},
		}

		markdown := report.ToMarkdown()

		assert.Contains(t, markdown, "# Migration Report")
		assert.Contains(t, markdown, "**Success Rate:** 0.0%")
		assert.NotContains(t, markdown, "## Successfully Migrated Plugins")
		assert.NotContains(t, markdown, "## Unsupported Plugins")
		assert.NotContains(t, markdown, "## Errors")
		assert.NotContains(t, markdown, "## Warnings")
	})

	t.Run("handles plugin without notes", func(t *testing.T) {
		report := &MigrationReport{
			SourceFile: "test.conf",
			TargetFile: "test.toml",
			Timestamp:  time.Now(),
			SupportedPlugins: []PluginMigration{
				{
					PluginName:       "grok",
					PluginType:       PluginTypeFilter,
					VectorComponents: []string{"remap_0"},
					Notes:            "", // No notes
				},
			},
		}

		markdown := report.ToMarkdown()

		assert.Contains(t, markdown, "grok (filter)")
		assert.Contains(t, markdown, "remap_0")
		// Should not have a Notes line when empty
		lines := strings.Split(markdown, "\n")
		hasNotesLine := false
		for _, line := range lines {
			if strings.Contains(line, "**Notes:**") {
				hasNotesLine = true
				break
			}
		}
		assert.False(t, hasNotesLine, "Should not include Notes line when empty")
	})

	t.Run("handles unsupported plugin without alternatives", func(t *testing.T) {
		report := &MigrationReport{
			SourceFile: "test.conf",
			TargetFile: "test.toml",
			Timestamp:  time.Now(),
			UnsupportedPlugins: []UnsupportedPlugin{
				{
					PluginName:         "custom_plugin",
					PluginType:         PluginTypeFilter,
					LineNumber:         20,
					VectorAlternatives: []string{}, // No alternatives
				},
			},
		}

		markdown := report.ToMarkdown()

		assert.Contains(t, markdown, "custom_plugin")
		assert.NotContains(t, markdown, "**Vector Alternatives:**")
	})
}

func TestMigrationResult_AddReport(t *testing.T) {
	t.Run("adds report and increments counters", func(t *testing.T) {
		result := &MigrationResult{}

		report := MigrationReport{
			SourceFile: "test.conf",
			Errors:     []MigrationError{},
		}

		result.AddReport(report)

		assert.Len(t, result.Reports, 1)
		assert.Equal(t, 1, result.TotalFiles)
		assert.Equal(t, 1, result.SuccessCount)
		assert.Equal(t, 0, result.FailureCount)
	})

	t.Run("classifies report with errors as failure", func(t *testing.T) {
		result := &MigrationResult{}

		report := MigrationReport{
			SourceFile: "test.conf",
			Errors: []MigrationError{
				{Message: "Error occurred"},
			},
		}

		result.AddReport(report)

		assert.Equal(t, 1, result.TotalFiles)
		assert.Equal(t, 0, result.SuccessCount)
		assert.Equal(t, 1, result.FailureCount)
	})

	t.Run("handles multiple reports", func(t *testing.T) {
		result := &MigrationResult{}

		// Add successful report
		result.AddReport(MigrationReport{
			SourceFile: "success1.conf",
			Errors:     []MigrationError{},
		})

		// Add failed report
		result.AddReport(MigrationReport{
			SourceFile: "failed1.conf",
			Errors:     []MigrationError{{Message: "Error"}},
		})

		// Add another successful report
		result.AddReport(MigrationReport{
			SourceFile: "success2.conf",
			Errors:     []MigrationError{},
		})

		assert.Len(t, result.Reports, 3)
		assert.Equal(t, 3, result.TotalFiles)
		assert.Equal(t, 2, result.SuccessCount)
		assert.Equal(t, 1, result.FailureCount)
	})

	t.Run("preserves report order", func(t *testing.T) {
		result := &MigrationResult{}

		filenames := []string{"first.conf", "second.conf", "third.conf"}
		for _, filename := range filenames {
			result.AddReport(MigrationReport{
				SourceFile: filename,
				Errors:     []MigrationError{},
			})
		}

		assert.Len(t, result.Reports, 3)
		for i, filename := range filenames {
			assert.Equal(t, filename, result.Reports[i].SourceFile)
		}
	})

	t.Run("handles report with multiple errors as single failure", func(t *testing.T) {
		result := &MigrationResult{}

		report := MigrationReport{
			SourceFile: "test.conf",
			Errors: []MigrationError{
				{Message: "Error 1"},
				{Message: "Error 2"},
				{Message: "Error 3"},
			},
		}

		result.AddReport(report)

		// Should count as one failure even with multiple errors
		assert.Equal(t, 1, result.TotalFiles)
		assert.Equal(t, 0, result.SuccessCount)
		assert.Equal(t, 1, result.FailureCount)
	})
}

func TestPluginMigration(t *testing.T) {
	t.Run("creates valid plugin migration", func(t *testing.T) {
		pm := PluginMigration{
			PluginName:       "file",
			PluginType:       PluginTypeInput,
			VectorComponents: []string{"file_source_0"},
			Notes:            "Test notes",
		}

		assert.Equal(t, "file", pm.PluginName)
		assert.Equal(t, PluginTypeInput, pm.PluginType)
		assert.Len(t, pm.VectorComponents, 1)
		assert.Equal(t, "Test notes", pm.Notes)
	})
}

func TestUnsupportedPlugin(t *testing.T) {
	t.Run("creates valid unsupported plugin", func(t *testing.T) {
		up := UnsupportedPlugin{
			PluginName:              "kafka",
			PluginType:              PluginTypeInput,
			LineNumber:              42,
			OriginalConfig:          "kafka { }",
			ManualMigrationGuidance: "Use kafka source",
			VectorAlternatives:      []string{"kafka", "http"},
		}

		assert.Equal(t, "kafka", up.PluginName)
		assert.Equal(t, PluginTypeInput, up.PluginType)
		assert.Equal(t, 42, up.LineNumber)
		assert.Len(t, up.VectorAlternatives, 2)
	})
}
