package validator

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestIsVectorInstalled(t *testing.T) {
	t.Run("checks if vector is in PATH", func(t *testing.T) {
		// This test verifies the function works, but result depends on environment
		result := isVectorInstalled()

		// Verify it returns a boolean (no panic or error)
		assert.IsType(t, false, result)

		// If vector is installed, verify we can find it
		if result {
			_, err := exec.LookPath("vector")
			assert.NoError(t, err)
		}
	})
}

func TestGetVectorVersion(t *testing.T) {
	// Skip if vector not installed
	if !isVectorInstalled() {
		t.Skip("Vector CLI not installed, skipping version test")
	}

	t.Run("returns vector version", func(t *testing.T) {
		version, err := GetVectorVersion()

		assert.NoError(t, err)
		assert.NotEmpty(t, version)
		// Version should contain "vector"
		assert.Contains(t, version, "vector")
	})
}

func TestValidateVectorConfig(t *testing.T) {
	// Create temporary test directory
	tmpDir, err := os.MkdirTemp("", "lv-go-validator-test-*")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	t.Run("validates valid Vector config", func(t *testing.T) {
		validConfig := `
[sources.file_source_0]
type = "file"
include = ["/var/log/*.log"]
read_from = "end"

[sinks.file_sink_0]
type = "file"
inputs = ["file_source_0"]
path = "/tmp/output.log"

[sinks.file_sink_0.encoding]
codec = "json"
`
		configPath := filepath.Join(tmpDir, "valid.toml")
		err := os.WriteFile(configPath, []byte(validConfig), 0644)
		require.NoError(t, err)

		valid, output, err := ValidateVectorConfig(configPath)

		if !isVectorInstalled() {
			// If vector not installed, validation should pass with warning
			assert.True(t, valid)
			assert.Contains(t, output, "skipping validation")
		} else {
			// If vector is installed, this should validate successfully
			assert.NoError(t, err)
			assert.True(t, valid)
			assert.NotEmpty(t, output)
		}
	})

	t.Run("detects invalid Vector config", func(t *testing.T) {
		invalidConfig := `
[sources.file_source_0]
invalid toml syntax here
type = "file"
`
		configPath := filepath.Join(tmpDir, "invalid.toml")
		err := os.WriteFile(configPath, []byte(invalidConfig), 0644)
		require.NoError(t, err)

		valid, output, err := ValidateVectorConfig(configPath)

		if !isVectorInstalled() {
			// If vector not installed, validation should pass with warning
			assert.True(t, valid)
			assert.Contains(t, output, "skipping validation")
		} else {
			// If vector is installed, should detect invalid syntax
			assert.False(t, valid)
			assert.NotEmpty(t, output)
		}
	})

	t.Run("handles non-existent config file", func(t *testing.T) {
		nonExistentPath := filepath.Join(tmpDir, "nonexistent.toml")

		valid, output, _ := ValidateVectorConfig(nonExistentPath)

		if !isVectorInstalled() {
			// If vector not installed, validation should pass with warning
			assert.True(t, valid)
			assert.Contains(t, output, "skipping validation")
		} else {
			// Vector should fail to validate non-existent file
			assert.False(t, valid)
			assert.NotEmpty(t, output)
		}
	})

	t.Run("handles missing required fields", func(t *testing.T) {
		incompleteConfig := `
[sources.file_source_0]
type = "file"
# Missing required 'include' field
`
		configPath := filepath.Join(tmpDir, "incomplete.toml")
		err := os.WriteFile(configPath, []byte(incompleteConfig), 0644)
		require.NoError(t, err)

		valid, output, err := ValidateVectorConfig(configPath)

		if !isVectorInstalled() {
			assert.True(t, valid)
			assert.Contains(t, output, "skipping validation")
		} else {
			// Vector should detect missing required field
			assert.False(t, valid)
			assert.NotEmpty(t, output)
		}
	})

	t.Run("validates config with transforms", func(t *testing.T) {
		configWithTransform := `
[sources.file_source_0]
type = "file"
include = ["/var/log/*.log"]

[transforms.remap_0]
type = "remap"
inputs = ["file_source_0"]
source = '''
. = parse_groks!(.message, ["%{COMMONAPACHELOG}"])
'''

[sinks.file_sink_0]
type = "file"
inputs = ["remap_0"]
path = "/tmp/output.log"

[sinks.file_sink_0.encoding]
codec = "json"
`
		configPath := filepath.Join(tmpDir, "with_transform.toml")
		err := os.WriteFile(configPath, []byte(configWithTransform), 0644)
		require.NoError(t, err)

		valid, output, err := ValidateVectorConfig(configPath)

		if !isVectorInstalled() {
			assert.True(t, valid)
			assert.Contains(t, output, "skipping validation")
		} else {
			// Should validate successfully with transform
			assert.NoError(t, err)
			assert.True(t, valid)
			assert.NotEmpty(t, output)
		}
	})
}
