package transformer

import (
	"testing"

	"lv-go/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestGrokFilterTransformer(t *testing.T) {
	transformer := &GrokFilterTransformer{}

	t.Run("supports grok plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("grok"))
		assert.False(t, transformer.Supports("mutate"))
	})

	t.Run("transforms grok with single pattern", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "grok",
			Config: map[string]interface{}{
				"match": map[string]interface{}{
					"message": "%{COMBINEDAPACHELOG}",
				},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)
		assert.NotNil(t, component)
		assert.Equal(t, models.ComponentTypeTransform, component.ComponentType)
		assert.Equal(t, "remap", component.ComponentKind)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "parse_groks!")
		assert.Contains(t, source, ".message")
		// Verify proper VRL array syntax (not malformed)
		assert.Contains(t, source, `["%{COMBINEDAPACHELOG}"]`)
		assert.NotContains(t, source, `["%{COMBINEDAPACHELOG}", "]`) // Old buggy format
	})

	t.Run("transforms grok with multiple patterns", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "grok",
			Config: map[string]interface{}{
				"match": map[string]interface{}{
					"message": []interface{}{"%{SYSLOGLINE}", "%{COMMONAPACHELOG}"},
				},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "parse_groks!")
		// Check proper array formatting
		assert.Contains(t, source, `["%{SYSLOGLINE}", "%{COMMONAPACHELOG}"]`)
	})

	t.Run("handles empty config with TODO comment", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "grok",
			Config:     map[string]interface{}{},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "# TODO: Add grok patterns")
	})
}

func TestMutateFilterTransformer(t *testing.T) {
	transformer := &MutateFilterTransformer{}

	t.Run("supports mutate plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("mutate"))
		assert.False(t, transformer.Supports("grok"))
	})

	t.Run("transforms remove_field", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "mutate",
			Config: map[string]interface{}{
				"remove_field": []interface{}{"temp", "debug"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "del(.temp)")
		assert.Contains(t, source, "del(.debug)")
	})

	t.Run("transforms rename", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "mutate",
			Config: map[string]interface{}{
				"rename": map[string]interface{}{
					"old_field": "new_field",
				},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, ".new_field = .old_field")
		assert.Contains(t, source, "del(.old_field)")
	})

	t.Run("transforms add_field", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "mutate",
			Config: map[string]interface{}{
				"add_field": map[string]interface{}{
					"custom_field": "custom_value",
				},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, `.custom_field = "custom_value"`)
	})

	t.Run("transforms convert (type conversion)", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "mutate",
			Config: map[string]interface{}{
				"convert": map[string]interface{}{
					"age":     "integer",
					"score":   "float",
					"enabled": "boolean",
				},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "to_int!")
		assert.Contains(t, source, "to_float!")
		assert.Contains(t, source, "to_bool!")
	})
}

func TestDateFilterTransformer(t *testing.T) {
	transformer := &DateFilterTransformer{}

	t.Run("supports date plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("date"))
		assert.False(t, transformer.Supports("grok"))
	})

	t.Run("transforms ISO8601 format", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "date",
			Config: map[string]interface{}{
				"match": []interface{}{"timestamp", "ISO8601"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "parse_timestamp!")
		assert.Contains(t, source, ".timestamp")
		assert.Contains(t, source, `format: "%+"`)
		assert.Contains(t, source, ".@timestamp")
	})

	t.Run("transforms UNIX timestamp", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "date",
			Config: map[string]interface{}{
				"match": []interface{}{"unix_time", "UNIX"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, `format: "%s"`)
	})

	t.Run("transforms common Joda-Time patterns", func(t *testing.T) {
		testCases := []struct {
			jodaFormat     string
			strptimeFormat string
		}{
			{"yyyy-MM-dd HH:mm:ss", "%Y-%m-%d %H:%M:%S"},
			{"yyyy-MM-dd'T'HH:mm:ss", "%Y-%m-%dT%H:%M:%S"},
			{"dd/MMM/yyyy:HH:mm:ss Z", "%d/%b/%Y:%H:%M:%S %z"},
			{"MMM dd HH:mm:ss", "%b %d %H:%M:%S"},
		}

		for _, tc := range testCases {
			t.Run(tc.jodaFormat, func(t *testing.T) {
				plugin := models.LogstashPlugin{
					PluginType: models.PluginTypeFilter,
					PluginName: "date",
					Config: map[string]interface{}{
						"match": []interface{}{"timestamp", tc.jodaFormat},
					},
				}

				component, err := transformer.Transform(plugin)
				assert.NoError(t, err)

				source := component.Config["source"].(string)
				assert.Contains(t, source, tc.strptimeFormat)
			})
		}
	})

	t.Run("handles custom target field", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "date",
			Config: map[string]interface{}{
				"match":  []interface{}{"log_date", "ISO8601"},
				"target": "parsed_date",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, ".parsed_date =")
		assert.NotContains(t, source, ".@timestamp")
	})

	t.Run("handles string array match config", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeFilter,
			PluginName: "date",
			Config: map[string]interface{}{
				"match": []string{"timestamp", "ISO8601"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		source := component.Config["source"].(string)
		assert.Contains(t, source, "parse_timestamp!")
	})
}
