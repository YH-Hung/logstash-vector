package models

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestPluginType_String(t *testing.T) {
	tests := []struct {
		name     string
		plugin   PluginType
		expected string
	}{
		{
			name:     "input plugin",
			plugin:   PluginTypeInput,
			expected: "input",
		},
		{
			name:     "filter plugin",
			plugin:   PluginTypeFilter,
			expected: "filter",
		},
		{
			name:     "output plugin",
			plugin:   PluginTypeOutput,
			expected: "output",
		},
		{
			name:     "unknown plugin type",
			plugin:   PluginType(999),
			expected: "unknown",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.plugin.String()
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestComponentType_String(t *testing.T) {
	tests := []struct {
		name      string
		component ComponentType
		expected  string
	}{
		{
			name:      "source component",
			component: ComponentTypeSource,
			expected:  "source",
		},
		{
			name:      "transform component",
			component: ComponentTypeTransform,
			expected:  "transform",
		},
		{
			name:      "sink component",
			component: ComponentTypeSink,
			expected:  "sink",
		},
		{
			name:      "unknown component type",
			component: ComponentType(999),
			expected:  "unknown",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.component.String()
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestErrorType_String(t *testing.T) {
	tests := []struct {
		name      string
		errorType ErrorType
		expected  string
	}{
		{
			name:      "parse error",
			errorType: ErrorTypeParseError,
			expected:  "parse_error",
		},
		{
			name:      "validation error",
			errorType: ErrorTypeValidationError,
			expected:  "validation_error",
		},
		{
			name:      "transformation error",
			errorType: ErrorTypeTransformationError,
			expected:  "transformation_error",
		},
		{
			name:      "unknown error type",
			errorType: ErrorType(999),
			expected:  "unknown_error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.errorType.String()
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestPluginType_Constants(t *testing.T) {
	t.Run("constants have expected values", func(t *testing.T) {
		assert.Equal(t, PluginType(0), PluginTypeInput)
		assert.Equal(t, PluginType(1), PluginTypeFilter)
		assert.Equal(t, PluginType(2), PluginTypeOutput)
	})

	t.Run("constants are distinct", func(t *testing.T) {
		assert.NotEqual(t, PluginTypeInput, PluginTypeFilter)
		assert.NotEqual(t, PluginTypeFilter, PluginTypeOutput)
		assert.NotEqual(t, PluginTypeInput, PluginTypeOutput)
	})
}

func TestComponentType_Constants(t *testing.T) {
	t.Run("constants have expected values", func(t *testing.T) {
		assert.Equal(t, ComponentType(0), ComponentTypeSource)
		assert.Equal(t, ComponentType(1), ComponentTypeTransform)
		assert.Equal(t, ComponentType(2), ComponentTypeSink)
	})

	t.Run("constants are distinct", func(t *testing.T) {
		assert.NotEqual(t, ComponentTypeSource, ComponentTypeTransform)
		assert.NotEqual(t, ComponentTypeTransform, ComponentTypeSink)
		assert.NotEqual(t, ComponentTypeSource, ComponentTypeSink)
	})
}

func TestErrorType_Constants(t *testing.T) {
	t.Run("constants have expected values", func(t *testing.T) {
		assert.Equal(t, ErrorType(0), ErrorTypeParseError)
		assert.Equal(t, ErrorType(1), ErrorTypeValidationError)
		assert.Equal(t, ErrorType(2), ErrorTypeTransformationError)
	})

	t.Run("constants are distinct", func(t *testing.T) {
		assert.NotEqual(t, ErrorTypeParseError, ErrorTypeValidationError)
		assert.NotEqual(t, ErrorTypeValidationError, ErrorTypeTransformationError)
		assert.NotEqual(t, ErrorTypeParseError, ErrorTypeTransformationError)
	})
}
