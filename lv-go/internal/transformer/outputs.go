package transformer

import (
	"fmt"
	"strings"

	"github.com/yourusername/lv-go/internal/models"
)

// ElasticsearchOutputTransformer transforms Logstash elasticsearch output to Vector elasticsearch sink
type ElasticsearchOutputTransformer struct{}

func (t *ElasticsearchOutputTransformer) Supports(pluginName string) bool {
	return pluginName == "elasticsearch"
}

func (t *ElasticsearchOutputTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vectorConfig := make(map[string]interface{})
	comments := []string{}

	// Map hosts to endpoints
	if hostsValue, ok := config["hosts"]; ok {
		var hosts []string
		switch h := hostsValue.(type) {
		case string:
			hosts = []string{h}
		case []interface{}:
			for _, host := range h {
				hosts = append(hosts, fmt.Sprint(host))
			}
		case []string:
			hosts = h
		}

		// Ensure HTTP scheme is present
		endpoints := []string{}
		for _, host := range hosts {
			if !strings.HasPrefix(host, "http://") && !strings.HasPrefix(host, "https://") {
				host = "http://" + host
			}
			endpoints = append(endpoints, host)
		}

		vectorConfig["endpoints"] = endpoints
	} else {
		vectorConfig["endpoints"] = []string{"http://localhost:9200"}
	}

	// Set bulk mode (Vector default for Elasticsearch)
	vectorConfig["mode"] = "bulk"

	// Map index (note: Vector uses different templating)
	if index, ok := config["index"].(string); ok {
		// Logstash uses %{+FORMAT} for date formatting
		// Vector doesn't support this directly
		if strings.Contains(index, "%{") {
			comments = append(comments, fmt.Sprintf("TODO: Convert Logstash index template '%s' to Vector format", index))
			// Use base name without template
			baseIndex := strings.Split(index, "%{")[0]
			baseIndex = strings.TrimSuffix(baseIndex, "-")
			if baseIndex != "" {
				vectorConfig["index"] = baseIndex
			}
		} else {
			vectorConfig["index"] = index
		}
	}

	// Handle authentication
	if user, hasUser := config["user"].(string); hasUser || config["password"] != nil {
		password, _ := config["password"].(string)
		if !hasUser {
			user = "elastic"
		}

		vectorConfig["auth"] = map[string]interface{}{
			"strategy": "basic",
			"user":     user,
			"password": password,
		}
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeSink,
		ComponentKind: "elasticsearch",
		Config:        vectorConfig,
		Inputs:        []string{}, // Will be set by orchestrator
		Comments:      comments,
	}, nil
}

// FileOutputTransformer transforms Logstash file output to Vector file sink
type FileOutputTransformer struct{}

func (t *FileOutputTransformer) Supports(pluginName string) bool {
	return pluginName == "file"
}

func (t *FileOutputTransformer) Transform(plugin models.LogstashPlugin) (*models.VectorComponent, error) {
	config := plugin.Config
	vectorConfig := make(map[string]interface{})

	// Map path
	if path, ok := config["path"].(string); ok {
		vectorConfig["path"] = path
	} else {
		vectorConfig["path"] = "/var/log/vector-output.log"
	}

	// Map codec
	codec, _ := config["codec"].(string)
	if codec == "" {
		codec = "json_lines"
	}

	// Map Logstash codecs to Vector encodings
	codecMap := map[string]string{
		"json":       "json",
		"json_lines": "json",
		"line":       "text",
		"plain":      "text",
		"rubydebug":  "json", // Approximate
	}

	vectorCodec := codecMap[codec]
	if vectorCodec == "" {
		vectorCodec = "json"
	}

	vectorConfig["encoding"] = map[string]interface{}{
		"codec": vectorCodec,
	}

	return &models.VectorComponent{
		ComponentType: models.ComponentTypeSink,
		ComponentKind: "file",
		Config:        vectorConfig,
		Inputs:        []string{}, // Will be set by orchestrator
		Comments:      []string{},
	}, nil
}
