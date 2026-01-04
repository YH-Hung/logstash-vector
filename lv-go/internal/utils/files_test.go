package utils

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestFindConfFiles(t *testing.T) {
	t.Run("finds conf files in flat directory", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create test files
		confFile1 := filepath.Join(tmpDir, "test1.conf")
		confFile2 := filepath.Join(tmpDir, "test2.conf")
		otherFile := filepath.Join(tmpDir, "test.txt")

		require.NoError(t, os.WriteFile(confFile1, []byte("input {}"), 0644))
		require.NoError(t, os.WriteFile(confFile2, []byte("output {}"), 0644))
		require.NoError(t, os.WriteFile(otherFile, []byte("text"), 0644))

		// Find .conf files
		files, err := FindConfFiles(tmpDir)

		require.NoError(t, err)
		assert.Len(t, files, 2)
		assert.Contains(t, files, confFile1)
		assert.Contains(t, files, confFile2)
		assert.NotContains(t, files, otherFile)
	})

	t.Run("finds conf files recursively in nested directories", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create nested structure
		subDir1 := filepath.Join(tmpDir, "sub1")
		subDir2 := filepath.Join(tmpDir, "sub1", "sub2")
		require.NoError(t, os.MkdirAll(subDir2, 0755))

		// Create .conf files at different levels
		rootConf := filepath.Join(tmpDir, "root.conf")
		sub1Conf := filepath.Join(subDir1, "sub1.conf")
		sub2Conf := filepath.Join(subDir2, "sub2.conf")

		require.NoError(t, os.WriteFile(rootConf, []byte("input {}"), 0644))
		require.NoError(t, os.WriteFile(sub1Conf, []byte("filter {}"), 0644))
		require.NoError(t, os.WriteFile(sub2Conf, []byte("output {}"), 0644))

		// Find all .conf files
		files, err := FindConfFiles(tmpDir)

		require.NoError(t, err)
		assert.Len(t, files, 3)
		assert.Contains(t, files, rootConf)
		assert.Contains(t, files, sub1Conf)
		assert.Contains(t, files, sub2Conf)
	})

	t.Run("returns empty slice when no conf files found", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create non-.conf files
		require.NoError(t, os.WriteFile(filepath.Join(tmpDir, "test.txt"), []byte("text"), 0644))
		require.NoError(t, os.WriteFile(filepath.Join(tmpDir, "test.toml"), []byte("toml"), 0644))

		files, err := FindConfFiles(tmpDir)

		require.NoError(t, err)
		assert.Empty(t, files)
	})

	t.Run("returns error for non-existent directory", func(t *testing.T) {
		nonExistentDir := "/path/to/nonexistent/directory"

		files, err := FindConfFiles(nonExistentDir)

		assert.Error(t, err)
		assert.Nil(t, files)
	})

	t.Run("sorts files alphabetically", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create files in non-alphabetical order
		files := []string{"zebra.conf", "alpha.conf", "beta.conf"}
		for _, file := range files {
			require.NoError(t, os.WriteFile(filepath.Join(tmpDir, file), []byte("test"), 0644))
		}

		foundFiles, err := FindConfFiles(tmpDir)

		require.NoError(t, err)
		assert.Len(t, foundFiles, 3)
		// Verify alphabetical ordering
		assert.Contains(t, foundFiles[0], "alpha.conf")
		assert.Contains(t, foundFiles[1], "beta.conf")
		assert.Contains(t, foundFiles[2], "zebra.conf")
	})

	t.Run("handles directory with mixed file types", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create various file types
		extensions := []string{".conf", ".txt", ".toml", ".json", ".yaml", ".log"}
		for _, ext := range extensions {
			filename := filepath.Join(tmpDir, "test"+ext)
			require.NoError(t, os.WriteFile(filename, []byte("content"), 0644))
		}

		files, err := FindConfFiles(tmpDir)

		require.NoError(t, err)
		assert.Len(t, files, 1, "should only find .conf files")
		assert.Contains(t, files[0], ".conf")
	})
}

func TestFileExists(t *testing.T) {
	t.Run("returns true for existing file", func(t *testing.T) {
		tmpDir := t.TempDir()
		testFile := filepath.Join(tmpDir, "test.conf")
		require.NoError(t, os.WriteFile(testFile, []byte("test"), 0644))

		exists := FileExists(testFile)

		assert.True(t, exists)
	})

	t.Run("returns false for non-existent file", func(t *testing.T) {
		nonExistentFile := filepath.Join(t.TempDir(), "nonexistent.conf")

		exists := FileExists(nonExistentFile)

		assert.False(t, exists)
	})

	t.Run("returns true for existing directory", func(t *testing.T) {
		tmpDir := t.TempDir()

		exists := FileExists(tmpDir)

		assert.True(t, exists, "directories should be considered as existing")
	})

	t.Run("returns false for invalid path", func(t *testing.T) {
		invalidPath := "/path/to/nonexistent/file.conf"

		exists := FileExists(invalidPath)

		assert.False(t, exists)
	})

	t.Run("handles symlinks to existing files", func(t *testing.T) {
		tmpDir := t.TempDir()
		realFile := filepath.Join(tmpDir, "real.conf")
		symLink := filepath.Join(tmpDir, "link.conf")

		require.NoError(t, os.WriteFile(realFile, []byte("test"), 0644))
		require.NoError(t, os.Symlink(realFile, symLink))

		exists := FileExists(symLink)

		assert.True(t, exists, "symlink to existing file should exist")
	})
}

func TestEnsureDir(t *testing.T) {
	t.Run("creates new directory", func(t *testing.T) {
		tmpDir := t.TempDir()
		newDir := filepath.Join(tmpDir, "newdir")

		err := EnsureDir(newDir)

		require.NoError(t, err)
		assert.True(t, FileExists(newDir))

		// Verify it's a directory
		info, err := os.Stat(newDir)
		require.NoError(t, err)
		assert.True(t, info.IsDir())
	})

	t.Run("does not error for existing directory", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Call EnsureDir on existing directory
		err := EnsureDir(tmpDir)

		require.NoError(t, err)
		assert.True(t, FileExists(tmpDir))
	})

	t.Run("creates nested directories", func(t *testing.T) {
		tmpDir := t.TempDir()
		nestedDir := filepath.Join(tmpDir, "a", "b", "c")

		err := EnsureDir(nestedDir)

		require.NoError(t, err)
		assert.True(t, FileExists(nestedDir))
		assert.True(t, FileExists(filepath.Join(tmpDir, "a")))
		assert.True(t, FileExists(filepath.Join(tmpDir, "a", "b")))
	})

	t.Run("sets correct permissions", func(t *testing.T) {
		tmpDir := t.TempDir()
		newDir := filepath.Join(tmpDir, "permtest")

		err := EnsureDir(newDir)
		require.NoError(t, err)

		// Check permissions (0755)
		info, err := os.Stat(newDir)
		require.NoError(t, err)

		// On Unix systems, should have rwxr-xr-x (0755)
		// Note: actual permissions may vary by OS and umask
		assert.True(t, info.IsDir())
		mode := info.Mode().Perm()
		// Check owner has read, write, execute
		assert.NotEqual(t, os.FileMode(0), mode&0700, "owner should have permissions")
	})

	t.Run("handles deeply nested paths", func(t *testing.T) {
		tmpDir := t.TempDir()
		deepPath := filepath.Join(tmpDir, "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")

		err := EnsureDir(deepPath)

		require.NoError(t, err)
		assert.True(t, FileExists(deepPath))
	})

	t.Run("handles path with spaces", func(t *testing.T) {
		tmpDir := t.TempDir()
		dirWithSpaces := filepath.Join(tmpDir, "dir with spaces")

		err := EnsureDir(dirWithSpaces)

		require.NoError(t, err)
		assert.True(t, FileExists(dirWithSpaces))
	})

	t.Run("handles path with special characters", func(t *testing.T) {
		tmpDir := t.TempDir()
		specialDir := filepath.Join(tmpDir, "dir-with_special.chars")

		err := EnsureDir(specialDir)

		require.NoError(t, err)
		assert.True(t, FileExists(specialDir))
	})
}
