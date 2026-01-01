package transformer

import (
	"fmt"

	"github.com/yourusername/lv-go/internal/models"
)

// FileInputTransformer transforms Logstash file input to Vector file source
type FileInputTransformer struct{}

func (t *FileInputTransformer) Supports(pluginName string) bool {
	return pluginName == "file"
}

func (t *FileInputTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vectorConfig := make(map[string]interface{})

	// Map path to include (Vector uses array)
	if pathValue, ok := config["path"]; ok {
		switch v := pathValue.(type) {
		case string:
			vectorConfig["include"] = []string{v}
		case []interface{}:
			paths := make([]string, len(v))
			for i, p := range v {
				paths[i] = fmt.Sprint(p)
			}
			vectorConfig["include"] = paths
		case []string:
			vectorConfig["include"] = v
		}
	} else {
		vectorConfig["include"] = []string{"/var/log/*.log"} // Default
	}

	// Map start_position to read_from
	startPosition, _ := config["start_position"].(string)
	if startPosition == "" {
		startPosition = "end"
	}

	if startPosition == "beginning" {
		vectorConfig["read_from"] = "beginning"
	} else {
		vectorConfig["read_from"] = "end"
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeSource,
		ComponentKind: "file",
		Config:        vectorConfig,
		Inputs:        []string{},
		Comments:      []string{},
	}, nil
}

// BeatsInputTransformer transforms Logstash beats input to Vector socket source
type BeatsInputTransformer struct{}

func (t *BeatsInputTransformer) Supports(pluginName string) bool {
	return pluginName == "beats"
}

func (t *BeatsInputTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config

	// Get port and host
	port := 5044
	if p, ok := config["port"].(int); ok {
		port = p
	}

	host := "0.0.0.0"
	if h, ok := config["host"].(string); ok {
		host = h
	}

	address := fmt.Sprintf("%s:%d", host, port)

	vectorConfig := map[string]interface{}{
		"address": address,
		"mode":    "tcp",
	}

	comments := []string{
		"NOTE: Beats input migrated to TCP socket",
		"For full Beats protocol support, consider using Filebeat → Vector directly",
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeSource,
		ComponentKind: "socket",
		Config:        vectorConfig,
		Inputs:        []string{},
		Comments:      comments,
	}, nil
}
