# Archived Datasets

This folder contains deprecated dataset versions kept for reference only.

## Why Archived

- `agent_analysis_golden_v1.json` - Superseded by v2 with improved schema and more examples

## Policy

- **Do not use** these datasets in new code
- **Do not delete** until confirmed no references exist
- Legacy code uses `LEGACY_NAME_MAP` in `__init__.py` for backwards compatibility

## Migration

Old code using `agent_analysis_golden_v1` will automatically resolve to archive path.
New code should use `golden/agent_analysis` instead.
