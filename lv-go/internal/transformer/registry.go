package transformer

import (
	"fmt"

	"github.com/yourusername/lv-go/internal/models"
)

// Registry holds all available transformers organized by plugin type
var Registry = map[models.PluginType][]Transformer{
	models.PluginTypeInput: {
		&FileInputTransformer{},
		&BeatsInputTransformer{},
	},
	models.PluginTypeFilter: {
		&GrokFilterTransformer{},
		&MutateFilterTransformer{},
		&DateFilterTransformer{},
	},
	models.PluginTypeOutput: {
		&ElasticsearchOutputTransformer{},
		&FileOutputTransformer{},
	},
}

// GetTransformer finds the appropriate transformer for a given plugin
func GetTransformer(pluginType models.PluginType, pluginName string) (Transformer, error) {
	transformers, ok := Registry[pluginType]
	if !ok {
		return nil, fmt.Errorf("no transformers registered for plugin type %s", pluginType)
	}

	for _, transformer := range transformers {
		if transformer.Supports(pluginName) {
			return transformer, nil
		}
	}

	return nil, fmt.Errorf("no transformer found for plugin %s (type: %s)", pluginName, pluginType)
}

// IsSupported checks if a plugin is supported
func IsSupported(pluginType models.PluginType, pluginName string) bool {
	_, err := GetTransformer(pluginType, pluginName)
	return err == nil
}
