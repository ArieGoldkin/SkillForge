---
description: Curate golden dataset entry
---
Follow SkillForge golden dataset curation process:

1. Ask for document path or content
2. Analyze document quality:
   - Accuracy and completeness
   - Relevance to codebase
   - Uniqueness (avoid duplicates)
3. Ask for category and tags
4. Validate entry against golden-dataset-validation skill
5. Add to: backend/data/golden_dataset/documents/

Entry format:
```markdown
# Document Title

## Metadata
- Path: `path/to/file.md`
- Category: `category-name`
- Tags: `tag1, tag2, tag3`
- Added: `YYYY-MM-DD`
- Curator: `human-name`

## Content
[Document content here]

## Use Cases
- Expected queries this document should answer
- Test scenarios to validate
```
