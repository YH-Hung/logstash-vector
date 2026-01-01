package models

// PluginType represents the type of Logstash plugin
type PluginType int

const (
	PluginTypeInput PluginType = iota
	PluginTypeFilter
	PluginTypeOutput
)

func (p PluginType) String() string {
	switch p {
	case PluginTypeInput:
		return "input"
	case PluginTypeFilter:
		return "filter"
	case PluginTypeOutput:
		return "output"
	default:
		return "unknown"
	}
}

// ComponentType represents the type of Vector component
type ComponentType int

const (
	ComponentTypeSource ComponentType = iota
	ComponentTypeTransform
	ComponentTypeSink
)

func (c ComponentType) String() string {
	switch c {
	case ComponentTypeSource:
		return "source"
	case ComponentTypeTransform:
		return "transform"
	case ComponentTypeSink:
		return "sink"
	default:
		return "unknown"
	}
}

// ErrorType represents the type of migration error
type ErrorType int

const (
	ErrorTypeParseError ErrorType = iota
	ErrorTypeValidationError
	ErrorTypeTransformationError
)

func (e ErrorType) String() string {
	switch e {
	case ErrorTypeParseError:
		return "parse_error"
	case ErrorTypeValidationError:
		return "validation_error"
	case ErrorTypeTransformationError:
		return "transformation_error"
	default:
		return "unknown_error"
	}
}
