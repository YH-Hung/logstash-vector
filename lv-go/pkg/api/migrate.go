package api

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/yourusername/lv-go/internal/generator"
	"github.com/yourusername/lv-go/internal/models"
	"github.com/yourusername/lv-go/internal/parser"
	"github.com/yourusername/lv-go/internal/report"
	"github.com/yourusername/lv-go/internal/transformer"
	"github.com/yourusername/lv-go/internal/utils"
	"github.com/yourusername/lv-go/internal/validator"
)

// MigrateConfig migrates a single Logstash configuration to Vector format
func MigrateConfig(logstashConfPath, outputPath string) (*models.VectorConfiguration, *models.MigrationReport, error) {
	// Determine output path
	if outputPath == "" {
		outputPath = strings.TrimSuffix(logstashConfPath, filepath.Ext(logstashConfPath)) + ".toml"
	}

	// Initialize report tracking
	supportedPlugins := []models.PluginMigration{}
	unsupportedPlugins := []models.UnsupportedPlugin{}
	errors := []models.MigrationError{}
	warnings := []string{}

	// Parse Logstash configuration
	logstashConfig, err := parser.ParseFile(logstashConfPath)
	if err != nil {
		errors = append(errors, models.MigrationError{
			ErrorType:  models.ErrorTypeParseError,
			Message:    fmt.Sprintf("Failed to parse file: %v", err),
			LineNumber: 0,
			FilePath:   logstashConfPath,
		})

		report := &models.MigrationReport{
			SourceFile:         logstashConfPath,
			TargetFile:         outputPath,
			Timestamp:          time.Now(),
			SupportedPlugins:   supportedPlugins,
			UnsupportedPlugins: unsupportedPlugins,
			Errors:             errors,
			Warnings:           warnings,
		}

		return nil, report, err
	}

	// Transform plugins to Vector components
	vectorConfig := &models.VectorConfiguration{
		Sources:    []models.VectorComponent{},
		Transforms: []models.VectorComponent{},
		Sinks:      []models.VectorComponent{},
	}

	// Keep track of component IDs for chaining
	sourceIDs := []string{}
	transformIDs := []string{}

	// Transform inputs → sources
	for idx, inputPlugin := range logstashConfig.Inputs {
		t, err := transformer.GetTransformer(inputPlugin.PluginType, inputPlugin.PluginName)

		if err != nil {
			// Unsupported plugin
			unsupportedReport := transformer.CreateUnsupportedReport(inputPlugin)
			unsupportedPlugins = append(unsupportedPlugins, unsupportedReport)
			continue
		}

		component, err := t.Transform(inputPlugin)
		if err != nil {
			errors = append(errors, models.MigrationError{
				ErrorType:  models.ErrorTypeTransformationError,
				Message:    fmt.Sprintf("Failed to transform %s input: %v", inputPlugin.PluginName, err),
				LineNumber: inputPlugin.LineNumber,
				FilePath:   logstashConfPath,
			})
			continue
		}

		// Generate component ID
		componentID := generator.GenerateComponentID(inputPlugin.PluginName, models.ComponentTypeSource, idx)
		component.ComponentID = componentID
		sourceIDs = append(sourceIDs, componentID)

		vectorConfig.AddSource(*component)

		supportedPlugins = append(supportedPlugins, models.PluginMigration{
			PluginName:       fmt.Sprintf("%s (input)", inputPlugin.PluginName),
			PluginType:       inputPlugin.PluginType,
			VectorComponents: []string{componentID},
			Notes:            fmt.Sprintf("Migrated to Vector %s source", component.ComponentKind),
		})
	}

	// Transform filters → transforms
	for idx, filterPlugin := range logstashConfig.Filters {
		t, err := transformer.GetTransformer(filterPlugin.PluginType, filterPlugin.PluginName)

		if err != nil {
			// Unsupported plugin
			unsupportedReport := transformer.CreateUnsupportedReport(filterPlugin)
			unsupportedPlugins = append(unsupportedPlugins, unsupportedReport)
			continue
		}

		component, err := t.Transform(filterPlugin)
		if err != nil {
			errors = append(errors, models.MigrationError{
				ErrorType:  models.ErrorTypeTransformationError,
				Message:    fmt.Sprintf("Failed to transform %s filter: %v", filterPlugin.PluginName, err),
				LineNumber: filterPlugin.LineNumber,
				FilePath:   logstashConfPath,
			})
			continue
		}

		// Generate component ID
		componentID := generator.GenerateComponentID(filterPlugin.PluginName, models.ComponentTypeTransform, idx)
		component.ComponentID = componentID

		// Set inputs to previous stage (sources or previous transforms)
		if len(transformIDs) > 0 {
			component.Inputs = []string{transformIDs[len(transformIDs)-1]}
		} else {
			component.Inputs = sourceIDs
		}

		transformIDs = append(transformIDs, componentID)
		vectorConfig.AddTransform(*component)

		supportedPlugins = append(supportedPlugins, models.PluginMigration{
			PluginName:       fmt.Sprintf("%s (filter)", filterPlugin.PluginName),
			PluginType:       filterPlugin.PluginType,
			VectorComponents: []string{componentID},
			Notes:            fmt.Sprintf("Migrated to Vector %s transform", component.ComponentKind),
		})
	}

	// Transform outputs → sinks
	for idx, outputPlugin := range logstashConfig.Outputs {
		t, err := transformer.GetTransformer(outputPlugin.PluginType, outputPlugin.PluginName)

		if err != nil {
			// Unsupported plugin
			unsupportedReport := transformer.CreateUnsupportedReport(outputPlugin)
			unsupportedPlugins = append(unsupportedPlugins, unsupportedReport)
			continue
		}

		component, err := t.Transform(outputPlugin)
		if err != nil {
			errors = append(errors, models.MigrationError{
				ErrorType:  models.ErrorTypeTransformationError,
				Message:    fmt.Sprintf("Failed to transform %s output: %v", outputPlugin.PluginName, err),
				LineNumber: outputPlugin.LineNumber,
				FilePath:   logstashConfPath,
			})
			continue
		}

		// Generate component ID
		componentID := generator.GenerateComponentID(outputPlugin.PluginName, models.ComponentTypeSink, idx)
		component.ComponentID = componentID

		// Set inputs to last stage (transforms or sources)
		if len(transformIDs) > 0 {
			component.Inputs = []string{transformIDs[len(transformIDs)-1]}
		} else {
			component.Inputs = sourceIDs
		}

		vectorConfig.AddSink(*component)

		supportedPlugins = append(supportedPlugins, models.PluginMigration{
			PluginName:       fmt.Sprintf("%s (output)", outputPlugin.PluginName),
			PluginType:       outputPlugin.PluginType,
			VectorComponents: []string{componentID},
			Notes:            fmt.Sprintf("Migrated to Vector %s sink", component.ComponentKind),
		})
	}

	// Validate we have at least one source and one sink
	if len(vectorConfig.Sources) == 0 {
		errors = append(errors, models.MigrationError{
			ErrorType:  models.ErrorTypeTransformationError,
			Message:    "No source components generated - cannot create valid Vector config",
			LineNumber: 0,
			FilePath:   logstashConfPath,
		})
	}
	if len(vectorConfig.Sinks) == 0 {
		errors = append(errors, models.MigrationError{
			ErrorType:  models.ErrorTypeTransformationError,
			Message:    "No sink components generated - cannot create valid Vector config",
			LineNumber: 0,
			FilePath:   logstashConfPath,
		})
	}

	// Create migration report
	migrationReport := &models.MigrationReport{
		SourceFile:         logstashConfPath,
		TargetFile:         outputPath,
		Timestamp:          time.Now(),
		SupportedPlugins:   supportedPlugins,
		UnsupportedPlugins: unsupportedPlugins,
		Errors:             errors,
		Warnings:           warnings,
	}

	// Return nil config if we have critical errors
	if len(vectorConfig.Sources) == 0 || len(vectorConfig.Sinks) == 0 {
		return nil, migrationReport, fmt.Errorf("migration failed: missing required components")
	}

	return vectorConfig, migrationReport, nil
}

// MigrateDirectory migrates all .conf files in a directory
func MigrateDirectory(directory, outputDir string, dryRun, validate bool) (*models.MigrationResult, error) {
	// Find all .conf files
	confFiles, err := utils.FindConfFiles(directory)
	if err != nil {
		return nil, fmt.Errorf("failed to find .conf files: %w", err)
	}

	if len(confFiles) == 0 {
		return nil, fmt.Errorf("no .conf files found in %s", directory)
	}

	// Ensure output directory exists (unless dry-run)
	if !dryRun && outputDir != "" {
		if err := utils.EnsureDir(outputDir); err != nil {
			return nil, fmt.Errorf("failed to create output directory: %w", err)
		}
	}

	result := &models.MigrationResult{
		Reports:      []models.MigrationReport{},
		TotalFiles:   len(confFiles),
		SuccessCount: 0,
		FailureCount: 0,
	}

	// Process each file
	for _, confFile := range confFiles {
		// Determine output path
		var outputPath string
		if outputDir != "" {
			baseName := filepath.Base(confFile)
			outputPath = filepath.Join(outputDir, strings.TrimSuffix(baseName, filepath.Ext(baseName))+".toml")
		} else {
			outputPath = strings.TrimSuffix(confFile, filepath.Ext(confFile)) + ".toml"
		}

		// Migrate the file
		vectorConfig, migrationReport, _ := MigrateConfig(confFile, outputPath)

		// Write the TOML file (unless dry-run)
		if !dryRun && vectorConfig != nil {
			tomlContent, err := generator.GenerateTOML(vectorConfig, confFile)
			if err != nil {
				migrationReport.Errors = append(migrationReport.Errors, models.MigrationError{
					ErrorType:  models.ErrorTypeTransformationError,
					Message:    fmt.Sprintf("Failed to generate TOML: %v", err),
					LineNumber: 0,
					FilePath:   confFile,
				})
			} else {
				// Write TOML file
				if err := os.WriteFile(outputPath, []byte(tomlContent), 0644); err != nil {
					migrationReport.Errors = append(migrationReport.Errors, models.MigrationError{
						ErrorType:  models.ErrorTypeTransformationError,
						Message:    fmt.Sprintf("Failed to write TOML file: %v", err),
						LineNumber: 0,
						FilePath:   outputPath,
					})
				}

				// Validate if requested
				if validate && len(migrationReport.Errors) == 0 {
					isValid, validationOutput, err := validator.ValidateVectorConfig(outputPath)
					if err != nil || !isValid {
						migrationReport.Errors = append(migrationReport.Errors, models.MigrationError{
							ErrorType:  models.ErrorTypeValidationError,
							Message:    fmt.Sprintf("Vector validation failed: %s", validationOutput),
							LineNumber: 0,
							FilePath:   outputPath,
						})
					}
				}
			}
		}

		result.AddReport(*migrationReport)
	}

	// Write combined report (unless dry-run)
	if !dryRun {
		reportPath := filepath.Join(directory, "migration-report.md")
		if outputDir != "" {
			reportPath = filepath.Join(outputDir, "migration-report.md")
		}

		if err := report.WriteCombinedReport(result.Reports, reportPath); err != nil {
			return result, fmt.Errorf("failed to write migration report: %w", err)
		}
	}

	return result, nil
}
