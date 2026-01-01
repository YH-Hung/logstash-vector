package utils

import (
	"os"
	"path/filepath"
	"sort"
)

// FindConfFiles recursively finds all .conf files in a directory
func FindConfFiles(directory string) ([]string, error) {
	var confFiles []string

	err := filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Check if file has .conf extension
		if filepath.Ext(path) == ".conf" {
			confFiles = append(confFiles, path)
		}

		return nil
	})

	if err != nil {
		return nil, err
	}

	// Sort files by name for consistent ordering
	sort.Strings(confFiles)

	return confFiles, nil
}

// FileExists checks if a file exists
func FileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// EnsureDir ensures a directory exists, creating it if necessary
func EnsureDir(path string) error {
	return os.MkdirAll(path, 0755)
}
