package models

// VectorComponent represents a single component in a Vector configuration
type VectorComponent struct {
	ComponentType ComponentType
	ComponentKind string // e.g., "file", "remap", "elasticsearch"
	ComponentID   string // e.g., "file_input_0"
	Config        map[string]interface{}
	Inputs        []string
	Comments      []string // For TODO markers and documentation
}

// VectorConfiguration represents a complete Vector configuration
type VectorConfiguration struct {
	Sources    []VectorComponent
	Transforms []VectorComponent
	Sinks      []VectorComponent
}

// AllComponents returns all components in order (sources, transforms, sinks)
func (vc *VectorConfiguration) AllComponents() []VectorComponent {
	all := make([]VectorComponent, 0, len(vc.Sources)+len(vc.Transforms)+len(vc.Sinks))
	all = append(all, vc.Sources...)
	all = append(all, vc.Transforms...)
	all = append(all, vc.Sinks...)
	return all
}

// AddSource adds a source component to the configuration
func (vc *VectorConfiguration) AddSource(component VectorComponent) {
	vc.Sources = append(vc.Sources, component)
}

// AddTransform adds a transform component to the configuration
func (vc *VectorConfiguration) AddTransform(component VectorComponent) {
	vc.Transforms = append(vc.Transforms, component)
}

// AddSink adds a sink component to the configuration
func (vc *VectorConfiguration) AddSink(component VectorComponent) {
	vc.Sinks = append(vc.Sinks, component)
}
