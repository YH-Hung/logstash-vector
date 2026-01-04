package transformer

import (
	"testing"

	"lv-go/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestFileInputTransformer(t *testing.T) {
	transformer := &FileInputTransformer{}

	t.Run("supports file plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("file"))
		assert.False(t, transformer.Supports("beats"))
	})

	t.Run("transforms basic file input", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "file",
			Config: map[string]interface{}{
				"path":           "/var/log/*.log",
				"start_position": "beginning",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)
		assert.NotNil(t, component)
		assert.Equal(t, models.ComponentTypeSource, component.ComponentType)
		assert.Equal(t, "file", component.ComponentKind)

		include := component.Config["include"].([]string)
		assert.Len(t, include, 1)
		assert.Contains(t, include, "/var/log/*.log")
		assert.Equal(t, "beginning", component.Config["read_from"])
	})

	t.Run("handles array of paths", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "file",
			Config: map[string]interface{}{
				"path": []interface{}{"/var/log/syslog", "/var/log/messages"},
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		include := component.Config["include"].([]string)
		assert.Len(t, include, 2)
		assert.Contains(t, include, "/var/log/syslog")
		assert.Contains(t, include, "/var/log/messages")
	})

	t.Run("defaults to end position", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "file",
			Config: map[string]interface{}{
				"path": "/var/log/*.log",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		assert.Equal(t, "end", component.Config["read_from"])
	})

	t.Run("uses default path if not specified", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "file",
			Config:     map[string]interface{}{},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		include := component.Config["include"].([]string)
		assert.Contains(t, include, "/var/log/*.log")
	})
}

func TestBeatsInputTransformer(t *testing.T) {
	transformer := &BeatsInputTransformer{}

	t.Run("supports beats plugin", func(t *testing.T) {
		assert.True(t, transformer.Supports("beats"))
		assert.False(t, transformer.Supports("file"))
	})

	t.Run("transforms beats input to socket", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "beats",
			Config: map[string]interface{}{
				"port": 5044,
				"host": "0.0.0.0",
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)
		assert.NotNil(t, component)
		assert.Equal(t, models.ComponentTypeSource, component.ComponentType)
		assert.Equal(t, "socket", component.ComponentKind)

		assert.Equal(t, "0.0.0.0:5044", component.Config["address"])
		assert.Equal(t, "tcp", component.Config["mode"])
	})

	t.Run("uses default port and host", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "beats",
			Config:     map[string]interface{}{},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		assert.Equal(t, "0.0.0.0:5044", component.Config["address"])
	})

	t.Run("includes migration notes", func(t *testing.T) {
		plugin := models.LogstashPlugin{
			PluginType: models.PluginTypeInput,
			PluginName: "beats",
			Config: map[string]interface{}{
				"port": 5044,
			},
		}

		component, err := transformer.Transform(plugin)
		assert.NoError(t, err)

		assert.NotEmpty(t, component.Comments)
		assert.Contains(t, component.Comments[0], "Beats input migrated to TCP socket")
	})
}
