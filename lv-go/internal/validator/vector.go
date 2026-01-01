package validator

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// ValidateVectorConfig runs 'vector validate' on a config file
func ValidateVectorConfig(configPath string) (bool, string, error) {
	// Check if vector is installed
	if !isVectorInstalled() {
		return false, "Vector CLI not found in PATH", nil
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Run vector validate command
	cmd := exec.CommandContext(ctx, "vector", "validate", configPath)
	output, err := cmd.CombinedOutput()

	if err != nil {
		// Check if it was a timeout
		if ctx.Err() == context.DeadlineExceeded {
			return false, "Validation timed out after 30 seconds", fmt.Errorf("timeout")
		}

		// Validation failed
		return false, string(output), nil
	}

	// Validation succeeded
	return true, string(output), nil
}

// isVectorInstalled checks if the vector binary is available
func isVectorInstalled() bool {
	cmd := exec.Command("which", "vector")
	err := cmd.Run()
	return err == nil
}

// GetVectorVersion returns the installed Vector version
func GetVectorVersion() (string, error) {
	cmd := exec.Command("vector", "--version")
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}

	// Parse version from output
	version := strings.TrimSpace(string(output))
	return version, nil
}
