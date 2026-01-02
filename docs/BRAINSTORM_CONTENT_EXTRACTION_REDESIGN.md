# Brainstorm: Content Extraction Redesign

**Date**: 2026-01-02
**Branch**: `issue/602-hyde-embeddings`
**Related Issues**: #602, #625

---

## Problem Statement

Our custom regex-based `content_cleaner.py` truncates **82.6% of article content** due to overly aggressive boilerplate detection patterns. The `sidebar` pattern matches legitimate table-of-contents headers like `### Sidebars`, discarding the majority of article content.

**Evidence**:

```
Jina API output:   65,405 bytes (8,048 words)
After cleaning:     7,304 bytes (423 words)
Content lost:       88.8%
```

This is a fundamental architecture problem, not just a regex bug fix.

---

## Current Architecture (Broken)

```
URL → JinaReader API → clean_extracted_content() → Database
                            ↑
                    Custom regex patterns
                    (END_CONTENT_INDICATORS)
                            ↑
                    "sidebar" pattern matches ToC
                            ↑
                    82% content DISCARDED
```

**Files**:

- `backend/app/shared/services/extraction/jina_reader.py` - Fetches from Jina API
- `backend/app/shared/services/extraction/content_cleaner.py` - Regex-based cleaning (THE PROBLEM)
- `backend/app/domains/analysis/workflows/tasks/extract_content.py` - Router

---

## Research Findings

### Benchmark Comparison (Scrapinghub Article Extraction Benchmark)

| Library | F1 Score | Precision | Recall | Notes |
| --- | --- | --- | --- | --- |
| **Trafilatura 2.0** | 0.958 | 0.938 | 0.978 | Best overall, ML-based |
| Readability-lxml | 0.922 | 0.913 | 0.931 | High predictability |
| Newspaper3k | 0.912 | 0.917 | 0.906 | News-specific |
| Custom regex | ~0.2* | ~0.9 | ~0.1 | Our current approach |

*Estimated based on 82% content loss

### Key Insight

> "Trafilatura consistently outperforms other open-source libraries in text extraction benchmarks, showcasing its efficiency and accuracy." - [Trafilatura Documentation](https://trafilatura.readthedocs.io/en/latest/evaluation.html)

### Trafilatura Features We Need

1. **`favor_recall=True`** - Include more content when unsure (our use case)
2. **ML-based boilerplate detection** - Not regex patterns
3. **No external API dependency** - Free, fast, self-hosted
4. **Already installed** - We have `trafilatura_extractor.py` but aren't using it!

---

## Solution Options

### Option A: Replace Jina + Custom Cleaner with Trafilatura

**Architecture**:

```
URL → TrafilaturaExtractor → Database
        (ML-based cleaning)
        (favor_recall=True)
```

**Pros**:

- F1 score: 0.958 (vs ~0.2 current)
- No external API (free, faster)
- No API rate limits
- Built-in metadata extraction

**Cons**:

- May not handle SPAs/JS-rendered pages
- No headless browser capability

**Implementation**:

```python
# extract_content.py
if is_arxiv_url(url):
    extractor = ArxivPDFExtractor()
elif is_youtube_url(url):
    extractor = YouTubeExtractor()
elif is_github_url(url):
    extractor = GitHubExtractor()
else:
    extractor = TrafilaturaExtractor()  # CHANGED from JinaReader
```

---

### Option B: Trafilatura Primary, Jina Fallback

**Architecture**:

```
URL → TrafilaturaExtractor → Quality Check
           ↓                      ↓
      Success (>1000 words)   Fail (<1000 words)
           ↓                      ↓
      Database ←←←←←←←←←←← JinaReader (fallback)
```

**Pros**:

- Best of both worlds
- Trafilatura handles 90%+ of cases
- Jina handles edge cases (SPAs, paywalls)
- Graceful degradation

**Cons**:

- More complex logic
- Two extraction paths to maintain

**Implementation**:

```python
async def extract_content(url: str, analysis_id: AnalysisID) -> dict:
    # Try Trafilatura first (free, fast, high accuracy)
    try:
        result = await TrafilaturaExtractor().extract_article(url)
        if result["word_count"] >= 500:  # Quality gate
            return result
        logger.warning("trafilatura_low_content", word_count=result["word_count"])
    except Exception as e:
        logger.warning("trafilatura_failed", error=str(e))

    # Fallback to Jina (handles SPAs, JS-rendered)
    return await JinaReader().extract_article(url)
```

---

### Option C: Use Trafilatura to Clean Jina's Raw Output

**Architecture**:

```
URL → JinaReader (raw HTML) → trafilatura.extract() → Database
           ↑                        ↑
      Jina handles SPAs      Trafilatura cleans
```

**Pros**:

- Jina handles complex pages
- Trafilatura's ML cleaning is superior
- No custom regex needed

**Cons**:

- Two dependencies
- Jina returns markdown, not HTML (trafilatura expects HTML)
- Complexity of format conversion

**Verdict**: Not recommended due to format mismatch.

---

### Option D: Fix Custom Cleaner (Quick Fix)

**Architecture**:

```
URL → JinaReader → Fixed clean_extracted_content() → Database
                        ↑
                 Remove "sidebar" pattern
                 Add quality gate (warn if >50% reduction)
```

**Pros**:

- Minimal code change
- Quick to implement

**Cons**:

- Doesn't solve fundamental problem
- Regex-based approach will have other edge cases
- F1 score will still be low

**Implementation**:

```python
# content_cleaner.py
END_CONTENT_INDICATORS = [
    # REMOVED: r"^#{1,3}\s*(?:footer|sidebar|widget)",
    r"^#{1,3}\s*(?:related articles?|more from)",
    r"^#{1,3}\s*(?:comments?|discussion)",
    # ... keep other safe patterns
]

# Add quality gate
if reduction_pct > 50:
    logger.error("excessive_content_reduction", ...)
    return content  # Return original, don't truncate
```

---

## Recommendation: Option B (Trafilatura Primary, Jina Fallback)

### Why Option B?

1. **Immediate Fix**: Trafilatura already installed, just need to wire it up
2. **High Accuracy**: F1 0.958 handles 95%+ of articles correctly
3. **Graceful Degradation**: Jina catches edge cases
4. **Cost Reduction**: Trafilatura is free (no API calls)
5. **Speed**: Trafilatura is faster (no network latency)

### Quality Gates

| Gate | Threshold | Action |
| --- | --- | --- |
| Minimum word count | 500 words | Try fallback |
| Maximum word count | 100,000 words | Truncate |
| Extraction failure | Exception | Try fallback |
| Fallback also fails | Exception | Fail with clear error |

### Implementation Plan

**Phase 1: Wire up Trafilatura with favor_recall (P0)**

1. Update `trafilatura_extractor.py` to use `favor_recall=True`
2. Add Trafilatura to extraction router as primary extractor
3. Remove `clean_extracted_content()` call from Jina path
4. Add quality gate for minimum word count

**Phase 2: Add Jina as Fallback (P1)**

1. Create fallback logic in `extract_content.py`
2. Add logging for which extractor succeeded
3. Add metrics for fallback rate

**Phase 3: Deprecate Custom Cleaner (P2)**

1. Remove regex-based `content_cleaner.py`
2. Keep only UTF-8 sanitization function
3. Update tests

---

## Updated File Changes

| File | Change | Priority |
| --- | --- | --- |
| `backend/app/shared/services/extraction/trafilatura_extractor.py` | Add `favor_recall=True` | P0 |
| `backend/app/domains/analysis/workflows/tasks/extract_content.py` | Use Trafilatura as primary | P0 |
| `backend/app/shared/services/extraction/jina_reader.py` | Remove `clean_extracted_content()` call | P0 |
| `backend/app/shared/services/extraction/__init__.py` | Export TrafilaturaExtractor | P0 |
| `backend/app/shared/services/extraction/content_cleaner.py` | Keep only UTF-8 sanitization | P2 |

---

## Verification Plan

### Test Cases

1. **Martin Fowler Microservices** - Must extract full 8,000+ words
2. **CSS-Tricks article** - Must extract full content
3. **Hacker News thread** - Should extract discussion
4. **Medium article** - May need Jina fallback (paywall)
5. **YouTube video** - Should use YouTubeExtractor (unchanged)
6. **GitHub README** - Should use GitHubExtractor (unchanged)

### Success Metrics

| Metric | Current | Target |
| --- | --- | --- |
| Average word count | 423 | 5,000+ |
| Content retention | 11% | 95%+ |
| Agent success rate | 0% | 100% |
| Quality gate pass rate | 0% | 90%+ |

---

## Sources

- [Trafilatura Documentation - Evaluation](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
- [Scrapinghub Article Extraction Benchmark](https://github.com/scrapinghub/article-extraction-benchmark)
- [Evaluating Text Extraction Tools for Python](https://adrien.barbaresi.eu/blog/evaluating-text-extraction-python.html)
- [Trafilatura Python Usage](https://trafilatura.readthedocs.io/en/latest/usage-python.html)
- [OSTI Evaluation of Content Extraction Libraries](https://www.osti.gov/servlets/purl/2429881)

---

## Decision Required

**Question**: Which option should we implement?

| Option | Effort | Risk | Benefit |
| --- | --- | --- | --- |
| A: Trafilatura only | Low | Medium (SPAs) | High |
| **B: Trafilatura + Jina fallback** | Medium | Low | Highest |
| C: Trafilatura cleans Jina | High | High | Medium |
| D: Fix regex patterns | Low | High | Low |

**Recommendation**: Option B provides the best balance of accuracy, robustness, and maintainability.

---

## Next Steps

1. [ ] Confirm approach with team
2. [ ] Update `trafilatura_extractor.py` with `favor_recall=True`
3. [ ] Wire Trafilatura as primary extractor
4. [ ] Add fallback logic for Jina
5. [ ] Test with Martin Fowler article
6. [ ] Verify agents produce real findings
7. [ ] Remove/deprecate custom content cleaner
