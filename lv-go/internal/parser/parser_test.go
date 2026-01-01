package parser

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/yourusername/lv-go/internal/models"
)

func TestParseFile(t *testing.T) {
	// Create a temporary test file
	tmpDir := t.TempDir()
	testFile := filepath.Join(tmpDir, "test.conf")

	content := `input {
  file {
    path => "/var/log/app.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
  }

  file {
    path => "/var/log/output.log"
  }
}
`

	err := os.WriteFile(testFile, []byte(content), 0644)
	require.NoError(t, err)

	// Parse the file
	config, err := ParseFile(testFile)
	require.NoError(t, err)
	require.NotNil(t, config)

	// Verify inputs
	assert.Len(t, config.Inputs, 1)
	assert.Equal(t, "file", config.Inputs[0].PluginName)
	assert.Equal(t, models.PluginTypeInput, config.Inputs[0].PluginType)
	assert.Equal(t, "/var/log/app.log", config.Inputs[0].Config["path"])
	assert.Equal(t, "beginning", config.Inputs[0].Config["start_position"])

	// Verify filters
	assert.Len(t, config.Filters, 1)
	assert.Equal(t, "grok", config.Filters[0].PluginName)
	assert.Equal(t, models.PluginTypeFilter, config.Filters[0].PluginType)

	// Verify outputs
	assert.Len(t, config.Outputs, 2)
	assert.Equal(t, "elasticsearch", config.Outputs[0].PluginName)
	assert.Equal(t, "file", config.Outputs[1].PluginName)
}

func TestParseFile_InvalidFile(t *testing.T) {
	_, err := ParseFile("/nonexistent/file.conf")
	assert.Error(t, err)
}

func TestParseFile_NoInputs(t *testing.T) {
	tmpDir := t.TempDir()
	testFile := filepath.Join(tmpDir, "test.conf")

	content := `output {
  file {
    path => "/var/log/output.log"
  }
}
`

	err := os.WriteFile(testFile, []byte(content), 0644)
	require.NoError(t, err)

	_, err = ParseFile(testFile)
	assert.Error(t, err)
}

func TestParseValue(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected interface{}
	}{
		{
			name:     "string value",
			input:    `"hello"`,
			expected: "hello",
		},
		{
			name:     "integer value",
			input:    "42",
			expected: 42,
		},
		{
			name:     "boolean true",
			input:    "true",
			expected: true,
		},
		{
			name:     "boolean false",
			input:    "false",
			expected: false,
		},
		{
			name:     "array value",
			input:    `["a", "b", "c"]`,
			expected: []string{"a", "b", "c"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := parseValue(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}
