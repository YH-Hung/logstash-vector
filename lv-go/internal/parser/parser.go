package parser

import (
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"unicode"

	"github.com/yourusername/lv-go/internal/models"
)

// block represents a top-level block in the Logstash config
type block struct {
	blockType string
	content   string
	start     int
}

// plugin represents a parsed plugin configuration
type plugin struct {
	name       string
	config     map[string]interface{}
	lineNumber int
}

// ParseFile parses a Logstash configuration file using regex-based parsing
func ParseFile(filePath string) (*models.LogstashConfiguration, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file %s: %w", filePath, err)
	}

	rawContent := string(content)

	// Extract top-level blocks
	blocks := extractBlocks(rawContent)

	inputs := []models.LogstashPlugin{}
	filters := []models.LogstashPlugin{}
	outputs := []models.LogstashPlugin{}

	for _, blk := range blocks {
		// Parse plugins within each block
		plugins := extractPlugins(blk.content, blk.start, rawContent)

		for _, p := range plugins {
			switch blk.blockType {
			case "input":
				inputs = append(inputs, models.LogstashPlugin{
					PluginType:   models.PluginTypeInput,
					PluginName:   p.name,
					Config:       p.config,
					LineNumber:   p.lineNumber,
					Conditionals: "",
				})
			case "filter":
				filters = append(filters, models.LogstashPlugin{
					PluginType:   models.PluginTypeFilter,
					PluginName:   p.name,
					Config:       p.config,
					LineNumber:   p.lineNumber,
					Conditionals: "",
				})
			case "output":
				outputs = append(outputs, models.LogstashPlugin{
					PluginType:   models.PluginTypeOutput,
					PluginName:   p.name,
					Config:       p.config,
					LineNumber:   p.lineNumber,
					Conditionals: "",
				})
			}
		}
	}

	config := &models.LogstashConfiguration{
		FilePath:   filePath,
		Inputs:     inputs,
		Filters:    filters,
		Outputs:    outputs,
		RawContent: rawContent,
	}

	// Validate configuration
	if err := config.Validate(); err != nil {
		return nil, err
	}

	return config, nil
}

// extractBlocks extracts top-level blocks (input, filter, output) by counting braces
func extractBlocks(content string) []block {
	blocks := []block{}
	blockKeywords := []string{"input", "filter", "output"}

	i := 0
	for i < len(content) {
		// Skip whitespace
		for i < len(content) && unicode.IsSpace(rune(content[i])) {
			i++
		}

		if i >= len(content) {
			break
		}

		// Check for block keyword
		foundKeyword := ""
		for _, keyword := range blockKeywords {
			if i+len(keyword) <= len(content) && strings.ToLower(content[i:i+len(keyword)]) == keyword {
				// Verify it's a whole word
				if i+len(keyword) < len(content) && (unicode.IsLetter(rune(content[i+len(keyword)])) || unicode.IsDigit(rune(content[i+len(keyword)]))) {
					continue
				}
				foundKeyword = keyword
				break
			}
		}

		if foundKeyword != "" {
			keywordStart := i
			i += len(foundKeyword)

			// Skip whitespace to find opening brace
			for i < len(content) && unicode.IsSpace(rune(content[i])) {
				i++
			}

			if i >= len(content) || content[i] != '{' {
				// Not a block, continue
				i++
				continue
			}

			// Found opening brace, count to find matching closing brace
			i++ // Skip opening brace
			braceDepth := 1
			contentStart := i

			for i < len(content) && braceDepth > 0 {
				if content[i] == '{' {
					braceDepth++
				} else if content[i] == '}' {
					braceDepth--
				}
				i++
			}

			// Extract block content (everything between the braces)
			blockContent := content[contentStart : i-1]
			blocks = append(blocks, block{
				blockType: strings.ToLower(foundKeyword),
				content:   blockContent,
				start:     keywordStart,
			})
		} else {
			i++
		}
	}

	return blocks
}

// extractPlugins extracts plugins from a block by finding plugin_name { ... } patterns
func extractPlugins(blockContent string, blockStart int, fullContent string) []plugin {
	plugins := []plugin{}

	i := 0
	for i < len(blockContent) {
		// Skip whitespace
		for i < len(blockContent) && unicode.IsSpace(rune(blockContent[i])) {
			i++
		}

		if i >= len(blockContent) {
			break
		}

		// Try to match identifier (plugin name)
		if unicode.IsLetter(rune(blockContent[i])) || blockContent[i] == '_' {
			nameStart := i
			for i < len(blockContent) && (unicode.IsLetter(rune(blockContent[i])) || unicode.IsDigit(rune(blockContent[i])) || blockContent[i] == '_') {
				i++
			}

			pluginName := blockContent[nameStart:i]

			// Skip whitespace to find opening brace
			for i < len(blockContent) && unicode.IsSpace(rune(blockContent[i])) {
				i++
			}

			if i >= len(blockContent) || blockContent[i] != '{' {
				// Not a plugin, continue
				continue
			}

			// Found opening brace, count to find matching closing brace
			i++ // Skip opening brace
			braceDepth := 1
			configStart := i

			for i < len(blockContent) && braceDepth > 0 {
				if blockContent[i] == '{' {
					braceDepth++
				} else if blockContent[i] == '}' {
					braceDepth--
				}
				i++
			}

			// Extract config content
			configContent := blockContent[configStart : i-1]
			configDict := parseConfig(configContent)

			// Calculate line number
			lineNumber := strings.Count(fullContent[:blockStart+nameStart], "\n") + 1

			plugins = append(plugins, plugin{
				name:       pluginName,
				config:     configDict,
				lineNumber: lineNumber,
			})
		} else {
			i++
		}
	}

	return plugins
}

// parseConfig parses configuration key => value pairs
func parseConfig(content string) map[string]interface{} {
	config := make(map[string]interface{})

	// Simple pattern to find key => markers
	kvPattern := regexp.MustCompile(`(\w+)\s*=>\s*`)
	matches := kvPattern.FindAllStringIndex(content, -1)

	for i, match := range matches {
		// Extract the key
		keyMatch := kvPattern.FindStringSubmatch(content[match[0]:match[1]])
		if len(keyMatch) < 2 {
			continue
		}
		key := keyMatch[1]

		// Find value start
		valueStart := match[1]

		// Find value end (next key or end of string)
		valueEnd := len(content)
		if i+1 < len(matches) {
			valueEnd = matches[i+1][0]
		}

		valueStr := strings.TrimSpace(content[valueStart:valueEnd])

		// Parse the value
		value := parseValue(valueStr)
		config[key] = value
	}

	return config
}

// parseValue parses a configuration value
func parseValue(valueStr string) interface{} {
	valueStr = strings.TrimSpace(valueStr)
	valueStr = strings.TrimSuffix(valueStr, ",")

	// String value
	if strings.HasPrefix(valueStr, `"`) || strings.HasPrefix(valueStr, `'`) {
		return strings.Trim(strings.Trim(valueStr, `"`), `'`)
	}

	// Array value
	if strings.HasPrefix(valueStr, "[") {
		arrayContent := strings.Trim(valueStr, "[]")
		items := []string{}
		for _, item := range strings.Split(arrayContent, ",") {
			trimmed := strings.TrimSpace(item)
			trimmed = strings.Trim(strings.Trim(trimmed, `"`), `'`)
			if trimmed != "" {
				items = append(items, trimmed)
			}
		}
		return items
	}

	// Hash/object value
	if strings.HasPrefix(valueStr, "{") {
		hashDict := make(map[string]interface{})
		hashContent := strings.Trim(valueStr, "{}")

		// Parse key => value pairs within the hash
		hashPattern := regexp.MustCompile(`"([^"]+)"\s*=>\s*"([^"]+)"`)
		hashMatches := hashPattern.FindAllStringSubmatch(hashContent, -1)

		for _, hMatch := range hashMatches {
			if len(hMatch) >= 3 {
				hashDict[hMatch[1]] = hMatch[2]
			}
		}

		if len(hashDict) > 0 {
			return hashDict
		}
		return valueStr
	}

	// Boolean
	if strings.ToLower(valueStr) == "true" || strings.ToLower(valueStr) == "false" {
		return strings.ToLower(valueStr) == "true"
	}

	// Number
	if num, err := strconv.Atoi(valueStr); err == nil {
		return num
	}

	// Default: return as string
	return valueStr
}
