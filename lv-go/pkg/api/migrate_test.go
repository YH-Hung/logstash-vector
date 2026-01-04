package api

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMigrateConfig(t *testing.T) {
	// Create temporary test directory
	tmpDir, err := os.MkdirTemp("", "lv-go-api-test-*")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	t.Run("migrates valid logstash config", func(t *testing.T) {
		logstashConfig := `
input {
  file {
    path => "/var/log/*.log"
    start_position => "beginning"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "logstash-2024.01.01"
  }
}
`
		// Write config to file
		configPath := filepath.Join(tmpDir, "valid.conf")
		err := os.WriteFile(configPath, []byte(logstashConfig), 0644)
		require.NoError(t, err)

		outputPath := filepath.Join(tmpDir, "valid_vector.toml")
		vectorConfig, report, err := MigrateConfig(configPath, outputPath)

		assert.NoError(t, err)
		assert.NotNil(t, vectorConfig)
		assert.NotNil(t, report)
		assert.NotEmpty(t, vectorConfig.Sources)
		assert.NotEmpty(t, vectorConfig.Sinks)
		assert.Empty(t, report.Errors)
	})

	t.Run("handles invalid logstash config", func(t *testing.T) {
		logstashConfig := `
input {
  invalid syntax here
}
`
		// Write config to file
		configPath := filepath.Join(tmpDir, "invalid.conf")
		err := os.WriteFile(configPath, []byte(logstashConfig), 0644)
		require.NoError(t, err)

		outputPath := filepath.Join(tmpDir, "invalid_vector.toml")
		vectorConfig, report, err := MigrateConfig(configPath, outputPath)

		assert.Error(t, err)
		assert.Nil(t, vectorConfig)
		assert.NotNil(t, report)
		assert.NotEmpty(t, report.Errors)
	})

	t.Run("generates report with unsupported plugins", func(t *testing.T) {
		logstashConfig := `
input {
  kafka {
    topics => ["my-topic"]
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
`
		// Write config to file
		configPath := filepath.Join(tmpDir, "unsupported.conf")
		err := os.WriteFile(configPath, []byte(logstashConfig), 0644)
		require.NoError(t, err)

		outputPath := filepath.Join(tmpDir, "unsupported_vector.toml")
		vectorConfig, report, err := MigrateConfig(configPath, outputPath)

		// Migration fails when only unsupported plugins exist
		assert.Error(t, err)
		assert.Nil(t, vectorConfig)
		assert.NotNil(t, report)
		assert.NotEmpty(t, report.UnsupportedPlugins)
	})

	t.Run("handles grok filter with multiple patterns", func(t *testing.T) {
		logstashConfig := `
input {
  file {
    path => "/var/log/*.log"
  }
}

filter {
  grok {
    match => { "message" => ["%{SYSLOGLINE}", "%{COMMONAPACHELOG}"] }
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
`
		// Write config to file
		configPath := filepath.Join(tmpDir, "grok.conf")
		err := os.WriteFile(configPath, []byte(logstashConfig), 0644)
		require.NoError(t, err)

		outputPath := filepath.Join(tmpDir, "grok_vector.toml")
		vectorConfig, report, err := MigrateConfig(configPath, outputPath)

		assert.NoError(t, err)
		assert.NotNil(t, vectorConfig)
		assert.NotNil(t, report)
		assert.NotEmpty(t, vectorConfig.Transforms)
		assert.Empty(t, report.Errors)
	})
}

func TestMigrateDirectory(t *testing.T) {
	t.Run("migrates multiple files in directory", func(t *testing.T) {
		// Create temporary test directory
		tmpDir, err := os.MkdirTemp("", "lv-go-test-*")
		require.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create test logstash configs
		config1 := `
input {
  file {
    path => "/var/log/app1.log"
  }
}
output {
  file {
    path => "/tmp/app1.log"
  }
}
`
		config2 := `
input {
  file {
    path => "/var/log/app2.log"
  }
}
output {
  elasticsearch {
    hosts => ["localhost:9200"]
  }
}
`
		err = os.WriteFile(filepath.Join(tmpDir, "app1.conf"), []byte(config1), 0644)
		require.NoError(t, err)
		err = os.WriteFile(filepath.Join(tmpDir, "app2.conf"), []byte(config2), 0644)
		require.NoError(t, err)

		result, err := MigrateDirectory(tmpDir, tmpDir, false, false)

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, 2, result.SuccessCount)
		assert.Equal(t, 0, result.FailureCount)
		assert.Len(t, result.Reports, 2)
	})

	t.Run("handles directory with mixed valid and invalid configs", func(t *testing.T) {
		testDir, err := os.MkdirTemp("", "lv-go-test-mixed-*")
		require.NoError(t, err)
		defer os.RemoveAll(testDir)

		validConfig := `
input {
  file {
    path => "/var/log/*.log"
  }
}
output {
  file {
    path => "/tmp/output.log"
  }
}
`
		invalidConfig := `
input {
  invalid syntax
}
`
		err = os.WriteFile(filepath.Join(testDir, "valid.conf"), []byte(validConfig), 0644)
		require.NoError(t, err)
		err = os.WriteFile(filepath.Join(testDir, "invalid.conf"), []byte(invalidConfig), 0644)
		require.NoError(t, err)

		result, err := MigrateDirectory(testDir, testDir, false, false)

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, 1, result.SuccessCount)
		assert.Equal(t, 1, result.FailureCount)
		assert.Len(t, result.Reports, 2)
	})

	t.Run("dry-run mode does not create output files", func(t *testing.T) {
		testDir, err := os.MkdirTemp("", "lv-go-test-dryrun-*")
		require.NoError(t, err)
		defer os.RemoveAll(testDir)

		config := `
input {
  file {
    path => "/var/log/*.log"
  }
}
output {
  file {
    path => "/tmp/output.log"
  }
}
`
		err = os.WriteFile(filepath.Join(testDir, "test.conf"), []byte(config), 0644)
		require.NoError(t, err)

		result, err := MigrateDirectory(testDir, testDir, true, false)

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, 1, result.SuccessCount)

		// Verify no .toml files were created (dry-run mode)
		files, err := filepath.Glob(filepath.Join(testDir, "*.toml"))
		require.NoError(t, err)
		assert.Empty(t, files)
	})

	t.Run("handles empty directory", func(t *testing.T) {
		emptyDir, err := os.MkdirTemp("", "lv-go-test-empty-*")
		require.NoError(t, err)
		defer os.RemoveAll(emptyDir)

		result, err := MigrateDirectory(emptyDir, emptyDir, false, false)

		assert.Error(t, err)
		// Result may be nil when error occurs
		if result != nil {
			assert.Equal(t, 0, result.SuccessCount)
		}
	})

	t.Run("handles non-existent directory", func(t *testing.T) {
		_, err := MigrateDirectory("/nonexistent/directory", "/tmp", false, false)

		assert.Error(t, err)
	})
}
