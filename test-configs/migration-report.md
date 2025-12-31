# Combined Migration Report

# Migration Report

**Source:** `../test-configs/simple-pipeline.conf`
**Target:** `../test-configs/simple-pipeline.toml`
**Generated:** 2025-12-31T11:17:21.843909
**Success Rate:** 100.0%

## Summary

- ✅ Successfully migrated: 6 plugins
- ⚠️  Unsupported plugins: 0
- ❌ Errors: 0
- ⚡ Warnings: 0

## Successfully Migrated Plugins

### file (input)
- **Vector components:** file_input_0
- **Notes:** Migrated to Vector file source

### grok (filter)
- **Vector components:** grok_filter_0
- **Notes:** Migrated to Vector remap transform

### mutate (filter)
- **Vector components:** mutate_filter_1
- **Notes:** Migrated to Vector remap transform

### date (filter)
- **Vector components:** date_filter_2
- **Notes:** Migrated to Vector remap transform

### elasticsearch (output)
- **Vector components:** elasticsearch_output_0
- **Notes:** Migrated to Vector elasticsearch sink

### file (output)
- **Vector components:** file_output_1
- **Notes:** Migrated to Vector file sink


---
