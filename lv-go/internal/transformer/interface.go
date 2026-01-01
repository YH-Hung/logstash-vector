package transformer

import "github.com/yourusername/lv-go/internal/models"

// Transformer defines the interface for transforming Logstash plugins to Vector components
type Transformer interface {
	// Supports checks if this transformer supports the given plugin name
	Supports(pluginName string) bool

	// Transform converts a Logstash plugin to a Vector component
	Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error)
}
