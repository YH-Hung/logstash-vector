package models

// LogstashPlugin represents a single plugin in a Logstash configuration
type LogstashPlugin struct {
	PluginType   PluginType
	PluginName   string
	Config       map[string]interface{}
	LineNumber   int
	Conditionals string // Not implemented yet, for future use
}

// LogstashConfiguration represents a complete Logstash configuration file
type LogstashConfiguration struct {
	FilePath   string
	Inputs     []LogstashPlugin
	Filters    []LogstashPlugin
	Outputs    []LogstashPlugin
	RawContent string
}

// Validate checks if the configuration is valid
func (lc *LogstashConfiguration) Validate() error {
	if len(lc.Inputs) == 0 {
		return &ValidationError{Message: "at least one input plugin is required"}
	}
	if len(lc.Outputs) == 0 {
		return &ValidationError{Message: "at least one output plugin is required"}
	}
	return nil
}

// ValidationError represents a validation error
type ValidationError struct {
	Message string
}

func (e *ValidationError) Error() string {
	return e.Message
}
