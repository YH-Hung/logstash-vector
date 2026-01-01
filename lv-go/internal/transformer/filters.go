package transformer

import (
	"fmt"
	"strings"

	"github.com/yourusername/lv-go/internal/models"
)

// GrokFilterTransformer transforms Logstash grok filter to Vector remap transform
type GrokFilterTransformer struct{}

func (t *GrokFilterTransformer) Supports(pluginName string) bool {
	return pluginName == "grok"
}

func (t *GrokFilterTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vrlLines := []string{}

	// Extract grok pattern from match config
	if matchConfig, ok := config["match"]; ok {
		if matchMap, ok := matchConfig.(map[string]interface{}); ok {
			for field, pattern := range matchMap {
				// Convert pattern to list if it's a string
				var patterns []string
				switch p := pattern.(type) {
				case string:
					patterns = []string{p}
				case []interface{}:
					for _, item := range p {
						patterns = append(patterns, fmt.Sprint(item))
					}
				case []string:
					patterns = p
				}

				// Build VRL pattern list
				patternsStr := `["` + strings.Join(patterns, `", "`) + `"]`
				vrlLines = append(vrlLines, fmt.Sprintf(". = parse_groks!(.%s, %s)", field, patternsStr))
			}
		}
	}

	// If no match config, add a comment
	if len(vrlLines) == 0 {
		vrlLines = append(vrlLines, "# TODO: Add grok patterns")
	}

	vectorConfig := map[string]interface{}{
		"source": strings.Join(vrlLines, "\n"),
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeTransform,
		ComponentKind: "remap",
		Config:        vectorConfig,
		Inputs:        []string{}, // Will be set by orchestrator
		Comments:      []string{},
	}, nil
}

// MutateFilterTransformer transforms Logstash mutate filter to Vector remap transform
type MutateFilterTransformer struct{}

func (t *MutateFilterTransformer) Supports(pluginName string) bool {
	return pluginName == "mutate"
}

func (t *MutateFilterTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vrlLines := []string{}

	// Handle remove_field
	if removeField, ok := config["remove_field"]; ok {
		var fields []string
		switch rf := removeField.(type) {
		case string:
			fields = []string{rf}
		case []interface{}:
			for _, f := range rf {
				fields = append(fields, fmt.Sprint(f))
			}
		case []string:
			fields = rf
		}

		for _, field := range fields {
			vrlLines = append(vrlLines, fmt.Sprintf("del(.%s)", field))
		}
	}

	// Handle rename
	if rename, ok := config["rename"]; ok {
		if renameMap, ok := rename.(map[string]interface{}); ok {
			for oldName, newName := range renameMap {
				vrlLines = append(vrlLines, fmt.Sprintf(".%s = .%s", newName, oldName))
				vrlLines = append(vrlLines, fmt.Sprintf("del(.%s)", oldName))
			}
		}
	}

	// Handle add_field
	if addField, ok := config["add_field"]; ok {
		if addMap, ok := addField.(map[string]interface{}); ok {
			for fieldName, fieldValue := range addMap {
				// Quote string values
				if strVal, ok := fieldValue.(string); ok {
					vrlLines = append(vrlLines, fmt.Sprintf(`.%s = "%s"`, fieldName, strVal))
				} else {
					vrlLines = append(vrlLines, fmt.Sprintf(".%s = %v", fieldName, fieldValue))
				}
			}
		}
	}

	// Handle convert (type conversion)
	if convert, ok := config["convert"]; ok {
		if convertMap, ok := convert.(map[string]interface{}); ok {
			typeMap := map[string]string{
				"integer": "int",
				"float":   "float",
				"string":  "string",
				"boolean": "bool",
			}

			for fieldName, targetType := range convertMap {
				targetTypeStr := fmt.Sprint(targetType)
				vrlType := typeMap[targetTypeStr]
				if vrlType == "" {
					vrlType = "string"
				}
				vrlLines = append(vrlLines, fmt.Sprintf(".%s = to_%s!(.%s)", fieldName, vrlType, fieldName))
			}
		}
	}

	if len(vrlLines) == 0 {
		vrlLines = append(vrlLines, "# TODO: Add mutate operations")
	}

	vectorConfig := map[string]interface{}{
		"source": strings.Join(vrlLines, "\n"),
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeTransform,
		ComponentKind: "remap",
		Config:        vectorConfig,
		Inputs:        []string{}, // Will be set by orchestrator
		Comments:      []string{},
	}, nil
}

// DateFilterTransformer transforms Logstash date filter to Vector remap transform
type DateFilterTransformer struct{}

func (t *DateFilterTransformer) Supports(pluginName string) bool {
	return pluginName == "date"
}

func (t *DateFilterTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vrlLines := []string{}

	// Extract match configuration
	if matchConfig, ok := config["match"]; ok {
		if matchList, ok := matchConfig.([]interface{}); ok && len(matchList) >= 2 {
			sourceField := fmt.Sprint(matchList[0])
			dateFormat := fmt.Sprint(matchList[1])

			// Convert Logstash date format to strptime format
			formatMap := map[string]string{
				"ISO8601": "%+",  // ISO 8601 format
				"UNIX":    "%s",  // Unix timestamp
				"UNIX_MS": "%s",  // Unix timestamp in milliseconds
			}

			vrlFormat := formatMap[dateFormat]
			if vrlFormat == "" {
				vrlFormat = dateFormat
			}

			// Determine target field
			targetField := "@timestamp"
			if target, ok := config["target"].(string); ok {
				targetField = target
			}

			// Generate VRL
			vrlLines = append(vrlLines, fmt.Sprintf(`.%s = parse_timestamp!(.%s, format: "%s")`, targetField, sourceField, vrlFormat))
		} else if matchList, ok := matchConfig.([]string); ok && len(matchList) >= 2 {
			sourceField := matchList[0]
			dateFormat := matchList[1]

			formatMap := map[string]string{
				"ISO8601": "%+",
				"UNIX":    "%s",
				"UNIX_MS": "%s",
			}

			vrlFormat := formatMap[dateFormat]
			if vrlFormat == "" {
				vrlFormat = dateFormat
			}

			targetField := "@timestamp"
			if target, ok := config["target"].(string); ok {
				targetField = target
			}

			vrlLines = append(vrlLines, fmt.Sprintf(`.%s = parse_timestamp!(.%s, format: "%s")`, targetField, sourceField, vrlFormat))
		} else {
			vrlLines = append(vrlLines, "# TODO: Configure date parsing")
		}
	} else {
		vrlLines = append(vrlLines, "# TODO: Configure date parsing")
	}

	vectorConfig := map[string]interface{}{
		"source": strings.Join(vrlLines, "\n"),
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeTransform,
		ComponentKind: "remap",
		Config:        vectorConfig,
		Inputs:        []string{}, // Will be set by orchestrator
		Comments:      []string{},
	}, nil
}
