package transformer

import (
	"fmt"
	"strings"

	"github.com/yourusername/lv-go/internal/models"
)

// CreateUnsupportedPlaceholder creates a placeholder component for unsupported plugins
func CreateUnsupportedPlaceholder(plugin models.LogstashPlugin) *models.VectorComponent {
	// Determine component type based on plugin type
	var componentType models.ComponentType
	switch plugin.PluginType {
	case models.PluginTypeInput:
		componentType = models.ComponentTypeSource
	case models.PluginTypeFilter:
		componentType = models.ComponentTypeTransform
	case models.PluginTypeOutput:
		componentType = models.ComponentTypeSink
	}

	// Create TODO comments with original config
	comments := []string{
		fmt.Sprintf("TODO: Manually migrate %s %s plugin", plugin.PluginType, plugin.PluginName),
		"",
		"Original Logstash configuration:",
	}

	// Add original config as comments
	configStr := formatConfig(plugin.Config, "")
	comments = append(comments, configStr)

	// Add migration guidance based on plugin type
	guidance := getPluginGuidance(plugin.PluginName, plugin.PluginType)
	if guidance != "" {
		comments = append(comments, "")
		comments = append(comments, "Migration guidance:")
		comments = append(comments, guidance)
	}

	// Create a minimal placeholder config
	placeholderConfig := map[string]interface{}{
		"_unsupported_plugin": plugin.PluginName,
		"_original_type":      plugin.PluginType.String(),
	}

	return &models.VectorComponent{
		ComponentType: componentType,
		ComponentKind: "remap", // Use remap as placeholder for most types
		Config:        placeholderConfig,
		Inputs:        []string{},
		Comments:      comments,
	}
}

// formatConfig formats a config map as a readable string
func formatConfig(config map[string]interface{}, indent string) string {
	var lines []string
	for key, value := range config {
		switch v := value.(type) {
		case string:
			lines = append(lines, fmt.Sprintf(`%s%s => "%s"`, indent, key, v))
		case []string:
			items := `["` + strings.Join(v, `", "`) + `"]`
			lines = append(lines, fmt.Sprintf("%s%s => %s", indent, key, items))
		case []interface{}:
			items := []string{}
			for _, item := range v {
				items = append(items, fmt.Sprintf(`"%v"`, item))
			}
			itemsStr := "[" + strings.Join(items, ", ") + "]"
			lines = append(lines, fmt.Sprintf("%s%s => %s", indent, key, itemsStr))
		case map[string]interface{}:
			lines = append(lines, fmt.Sprintf("%s%s => {", indent, key))
			lines = append(lines, formatConfig(v, indent+"  "))
			lines = append(lines, indent+"}")
		default:
			lines = append(lines, fmt.Sprintf("%s%s => %v", indent, key, v))
		}
	}
	return strings.Join(lines, "\n")
}

// getPluginGuidance provides migration guidance for common unsupported plugins
func getPluginGuidance(pluginName string, pluginType models.PluginType) string {
	guidance := map[string]string{
		"kafka": "The Logstash kafka plugin can be migrated to Vector's kafka source/sink.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/kafka/\n" +
			"     https://vector.dev/docs/reference/configuration/sinks/kafka/",
		"redis": "Consider using Vector's redis source/sink.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/redis/\n" +
			"     https://vector.dev/docs/reference/configuration/sinks/redis/",
		"http": "Vector has http source and http sink components.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/http/\n" +
			"     https://vector.dev/docs/reference/configuration/sinks/http/",
		"syslog": "Vector has native syslog source support.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/syslog/",
		"tcp": "Vector supports TCP via socket source/sink.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/socket/\n" +
			"     https://vector.dev/docs/reference/configuration/sinks/socket/",
		"udp": "Vector supports UDP via socket source/sink.\n" +
			"See: https://vector.dev/docs/reference/configuration/sources/socket/\n" +
			"     https://vector.dev/docs/reference/configuration/sinks/socket/",
		"ruby": "Ruby filter logic should be reimplemented in Vector Remap Language (VRL).\n" +
			"See: https://vector.dev/docs/reference/vrl/",
		"jdbc": "JDBC functionality is not directly available in Vector.\n" +
			"Consider using external tools or Vector's HTTP source with a database proxy.",
	}

	if g, ok := guidance[pluginName]; ok {
		return g
	}

	// Generic guidance based on plugin type
	switch pluginType {
	case models.PluginTypeInput:
		return "Search for equivalent Vector sources at:\n" +
			"https://vector.dev/docs/reference/configuration/sources/"
	case models.PluginTypeFilter:
		return "Consider implementing this logic in Vector Remap Language (VRL).\n" +
			"See: https://vector.dev/docs/reference/vrl/"
	case models.PluginTypeOutput:
		return "Search for equivalent Vector sinks at:\n" +
			"https://vector.dev/docs/reference/configuration/sinks/"
	}

	return ""
}

// CreateUnsupportedReport creates an UnsupportedPlugin report entry
func CreateUnsupportedReport(plugin models.LogstashPlugin) models.UnsupportedPlugin {
	// Format original config
	configStr := formatConfig(plugin.Config, "  ")

	// Get guidance
	guidance := getPluginGuidance(plugin.PluginName, plugin.PluginType)

	// Get vector alternatives
	alternatives := getVectorAlternatives(plugin.PluginName, plugin.PluginType)

	return models.UnsupportedPlugin{
		PluginName:              plugin.PluginName,
		PluginType:              plugin.PluginType,
		LineNumber:              plugin.LineNumber,
		OriginalConfig:          configStr,
		ManualMigrationGuidance: guidance,
		VectorAlternatives:      alternatives,
	}
}

// getVectorAlternatives returns a list of Vector alternatives for unsupported plugins
func getVectorAlternatives(pluginName string, pluginType models.PluginType) []string {
	alternatives := map[string][]string{
		"kafka": {
			"kafka source: https://vector.dev/docs/reference/configuration/sources/kafka/",
			"kafka sink: https://vector.dev/docs/reference/configuration/sinks/kafka/",
		},
		"redis": {
			"redis source: https://vector.dev/docs/reference/configuration/sources/redis/",
			"redis sink: https://vector.dev/docs/reference/configuration/sinks/redis/",
		},
		"http": {
			"http source: https://vector.dev/docs/reference/configuration/sources/http/",
			"http sink: https://vector.dev/docs/reference/configuration/sinks/http/",
		},
		"syslog": {
			"syslog source: https://vector.dev/docs/reference/configuration/sources/syslog/",
		},
		"ruby": {
			"remap transform: https://vector.dev/docs/reference/configuration/transforms/remap/",
		},
	}

	if alts, ok := alternatives[pluginName]; ok {
		return alts
	}

	// Generic alternatives based on plugin type
	switch pluginType {
	case models.PluginTypeInput:
		return []string{"https://vector.dev/docs/reference/configuration/sources/"}
	case models.PluginTypeFilter:
		return []string{"https://vector.dev/docs/reference/configuration/transforms/"}
	case models.PluginTypeOutput:
		return []string{"https://vector.dev/docs/reference/configuration/sinks/"}
	}

	return []string{}
}
