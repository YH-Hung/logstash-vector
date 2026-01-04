package transformer

import (
	"testing"

	"lv-go/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestElasticsearchOutputTransformer(t *testing.T) {
	transformer := &ElasticsearchOutputTransformer{}

	t.Run("supports elasticsearch plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("elasticsearch"))
		assert.False(t, transformer.Supports("file"))
	})

	t.Run("transforms basic elasticsearch output", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "elasticsearch",
			Config: map[string]interface{}{
				"hosts": []interface{}{"localhost:9200"},
				"index": "logstash-2024.01.01",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)
		assert.NotNil(t, component)
		assert.Equal(t, models.ComponentTypeSink, component.ComponentType)
		assert.Equal(t, "elasticsearch", component.ComponentKind)

		endpoints := component.Config["endpoints"].([]string)
		assert.Contains(t, endpoints, "http://localhost:9200")
		assert.Equal(t, "logstash-2024.01.01", component.Config["index"])
		assert.Equal(t, "bulk", component.Config["mode"])
	})

	t.Run("handles authentication", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "elasticsearch",
			Config: map[string]interface{}{
				"hosts":    []interface{}{"localhost:9200"},
				"user":     "elastic",
				"password": "changeme",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		auth := component.Config["auth"].(map[string]interface{})
		assert.Equal(t, "basic", auth["strategy"])
		assert.Equal(t, "elastic", auth["user"])
		assert.Equal(t, "changeme", auth["password"])
	})

	t.Run("adds http scheme if missing", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "elasticsearch",
			Config: map[string]interface{}{
				"hosts": []interface{}{"es1:9200", "https://es2:9200"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		endpoints := component.Config["endpoints"].([]string)
		assert.Contains(t, endpoints, "http://es1:9200")
		assert.Contains(t, endpoints, "https://es2:9200")
	})

	t.Run("handles dynamic index with TODO comment", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "elasticsearch",
			Config: map[string]interface{}{
				"hosts": []interface{}{"localhost:9200"},
				"index": "logstash-%{+YYYY.MM.dd}",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		// Should have TODO comment
		assert.NotEmpty(t, component.Comments)
		assert.Contains(t, component.Comments[0], "TODO")
		assert.Contains(t, component.Comments[0], "logstash-%{+YYYY.MM.dd}")

		// Should have base index name
		assert.Equal(t, "logstash", component.Config["index"])
	})

	t.Run("uses default values if not specified", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "elasticsearch",
			Config:     map[string]interface{}{},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		endpoints := component.Config["endpoints"].([]string)
		assert.Contains(t, endpoints, "http://localhost:9200")
		assert.Equal(t, "bulk", component.Config["mode"])
	})
}

func TestFileOutputTransformer(t *testing.T) {
	transformer := &FileOutputTransformer{}

	t.Run("supports file plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("file"))
		assert.False(t, transformer.Supports("elasticsearch"))
	})

	t.Run("transforms basic file output", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "file",
			Config: map[string]interface{}{
				"path":  "/var/log/output.log",
				"codec": "json_lines",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)
		assert.NotNil(t, component)
		assert.Equal(t, models.ComponentTypeSink, component.ComponentType)
		assert.Equal(t, "file", component.ComponentKind)

		assert.Equal(t, "/var/log/output.log", component.Config["path"])

		encoding := component.Config["encoding"].(map[string]interface{})
		assert.Equal(t, "json", encoding["codec"])
	})

	t.Run("maps codec to Vector encoding", func(t *testing.T) {
		testCases := []struct {
			logstashCodec string
			vectorCodec   string
		}{
			{"json", "json"},
			{"json_lines", "json"},
			{"line", "text"},
			{"plain", "text"},
			{"rubydebug", "json"},
		}

		for _, tc := range testCases {
			t.Run(tc.logstashCodec, func(t *testing.T) {
				plugin := models.LogstashPlugin{
					PluginType: models.PluginTypeOutput,
					PluginName: "file",
					Config: map[string]interface{}{
						"path":  "/tmp/test.log",
						"codec": tc.logstashCodec,
					},
				}

				component, err := transformer.Transform(plugin)
				assert.NoError(t, err)

				encoding := component.Config["encoding"].(map[string]interface{})
				assert.Equal(t, tc.vectorCodec, encoding["codec"])
			})
		}
	})

	t.Run("uses default path if not specified", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "file",
			Config:     map[string]interface{}{},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		assert.Equal(t, "/var/log/vector-output.log", component.Config["path"])
	})

	t.Run("defaults to json codec", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeOutput,
			PluginName: "file",
			Config: map[string]interface{}{
				"path": "/tmp/test.log",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		encoding := component.Config["encoding"].(map[string]interface{})
		assert.Equal(t, "json", encoding["codec"])
	})
}
