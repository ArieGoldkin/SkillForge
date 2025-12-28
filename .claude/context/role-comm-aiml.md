# AI/ML Engineer Communication Log

## Research: Ollama Python Integration Best Practices (December 2025)

**Date**: 2025-12-28
**Research Scope**: Latest Ollama Python integration patterns, langchain-ollama features, performance optimization for Apple Silicon M4 Max, CI/CD best practices

---

## 1. langchain-ollama Latest Version & Features

### Package Information
- **Latest Version**: 1.0.1 (Released December 12, 2025)
- **Python Requirements**: Python 3.10.0+ (< 4.0.0)
- **License**: MIT
- **Installation**: `pip install langchain-ollama`

### Key Components

#### ChatOllama
- Chat-based interactions with Ollama models
- Supports streaming, tool calling, and structured output
- Integration with LangChain agent workflows

#### OllamaEmbeddings
- Vector embeddings for semantic search and RAG applications
- Methods:
  - `embed_query()` - Single text embeddings
  - `embed_documents()` - Batch embeddings
- Seamless integration with vector stores (e.g., InMemoryVectorStore)

#### OllamaLLM (Legacy)
- Older interface for text completion
- Superseded by ChatOllama for new projects

### Documentation Resources
- **API Reference**: https://reference.langchain.com/python/integrations/langchain_ollama/
- **Conceptual Guides**: https://docs.langchain.com/oss/python/integrations/providers/ollama
- **GitHub**: langchain/partners/ollama

---

## 2. OllamaEmbeddings Class Usage

### Basic Setup

```python
from langchain_ollama import OllamaEmbeddings

# Initialize embeddings with model name
embeddings = OllamaEmbeddings(model="llama3")

# Single text embedding
vector = embeddings.embed_query("Sample text for embedding")

# Batch embeddings
vectors = embeddings.embed_documents([
    "First document text",
    "Second document text",
    "Third document text"
])
```

### Prerequisites
1. Install Ollama locally for your platform
2. Pull model: `ollama pull llama3` (or any embedding-optimized model)
3. Optional: Configure LangSmith for automated tracing

### RAG Integration Example

```python
from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

# Initialize embeddings
embeddings = OllamaEmbeddings(model="llama3")

# Create vector store
vector_store = InMemoryVectorStore(embeddings)

# Index documents
docs = ["Document 1", "Document 2", "Document 3"]
vector_store.add_documents(docs)

# Retrieve similar documents
results = vector_store.similarity_search("query text", k=3)
```

### Recommended Embedding Models
- **Nomic Embed Text**: High-performing with large token context window
- **BGE-M3**: Versatile (Multi-Functionality, Multi-Linguality, Multi-Granularity)
- **Llama 3**: General-purpose, good balance of quality and speed

---

## 3. ChatOllama Advanced Features

### Tool Calling Support

#### Compatible Models (Tool Support)
- Llama 3.1 (8B, 70B, 405B)
- Mistral Nemo
- Firefunction v2
- Command-R+

**Important**: Verify latest model versions with `ollama pull <model>`

#### Implementation Patterns

**Native Ollama SDK Approach**:
```python
from ollama import chat

# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform basic arithmetic operations",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            }
        }
    }
]

# Call with tools
response = chat(
    model='llama3.1',
    messages=[{'role': 'user', 'content': 'What is 15 + 27?'}],
    tools=tools
)

# Process tool calls
if response.get('tool_calls'):
    for tool_call in response['tool_calls']:
        # Execute tool and return result via message with 'tool' role
        tool_result = execute_tool(tool_call)
        messages.append({'role': 'tool', 'content': tool_result})
```

**OpenAI Compatibility Mode**:
Ollama supports OpenAI API format for drop-in replacement:
```python
# Use OpenAI client libraries with Ollama endpoint
# Point to http://localhost:11434/v1 for OpenAI-compatible API
```

**Planned Enhancements**:
- Streaming tool calls (faster multi-tool execution)
- Tool choice parameters (enforce specific tool usage)

### Streaming Responses

#### Synchronous Streaming
```python
from ollama import chat

response = chat(
    model='llama3.1',
    messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
    stream=True
)

for chunk in response:
    print(chunk['message']['content'], end='', flush=True)
```

#### Asynchronous Streaming
```python
from ollama import AsyncClient

async def stream_chat():
    client = AsyncClient()

    async for chunk in await client.chat(
        model='llama3.1',
        messages=[{'role': 'user', 'content': 'Explain quantum computing'}],
        stream=True
    ):
        print(chunk['message']['content'], end='', flush=True)
```

**Best Practice**: Use streaming for:
- Long-form content generation
- Real-time user feedback
- Reducing perceived latency
- Progress indication in UIs

### Structured Output (JSON Schema)

#### Overview
Ollama supports constraining model outputs to specific JSON schemas using the `format` parameter.

#### Capabilities
- Parsing data from documents
- Extracting data from images (with vision models)
- Structuring all language model responses
- Greater consistency than JSON mode alone

#### Implementation with Pydantic

```python
from ollama import chat
from pydantic import BaseModel

class UserProfile(BaseModel):
    name: str
    age: int
    email: str
    interests: list[str]

# Generate Pydantic JSON schema
schema = UserProfile.model_json_schema()

response = chat(
    model='llama3.1',
    messages=[{
        'role': 'user',
        'content': 'Extract user profile from: "John Doe, 32 years old, john@example.com, enjoys hiking and photography"'
    }],
    format=schema,
    options={'temperature': 0}  # Deterministic output
)

# Parse response
user = UserProfile.model_validate_json(response['message']['content'])
```

#### Compatible Models
- Llama 3.1 (text processing)
- Llama 3.2 Vision (image analysis with structured output)

#### Best Practices
1. Use schema validation libraries (Pydantic for Python, Zod for JavaScript)
2. Include "return as JSON" in prompts for clarity
3. Set temperature to 0 for deterministic outputs
4. Provide example outputs in prompts for better quality

#### Planned Enhancements
- Logits exposure
- Performance improvements
- GPU acceleration for schema validation
- Expanded format support beyond JSON schemas

---

## 4. Performance Optimization for Apple Silicon M4 Max

### Memory Requirements

| Model Size | Minimum RAM Required |
|-----------|---------------------|
| 7B models | 8 GB |
| 13B models | 16 GB |
| 33B models | 32 GB |
| 70B models | 64 GB |
| 405B models | Cloud-based (use `llama3.1:405b-cloud`) |

**M4 Max Configuration**:
- Base: 36GB unified memory → Can run up to 33B models locally
- Max: 128GB unified memory → Can run 70B+ models with headroom

### Native macOS Support
- Ollama provides native `.dmg` installer for macOS
- Optimized for Apple Silicon (Metal acceleration)
- **No Docker on Mac**: Docker Desktop doesn't support GPU passthrough on macOS - use native installation

### Configuration Parameters

#### Model Parameters (via Modelfile)
```
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096        # Context window size
PARAMETER num_thread 8        # CPU threads (adjust for M4 Max)
```

#### Environment Variables (Performance Tuning)

**Not explicitly documented by Ollama**, but common patterns:
- `OLLAMA_HOST`: Set API endpoint (default: http://localhost:11434)
- `OLLAMA_MODELS`: Custom model directory path
- Model-specific parameters via Modelfile `PARAMETER` directives

### API Endpoints

**REST API Base**: http://localhost:11434

```bash
# Generate endpoint
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1",
  "prompt": "Why is the sky blue?"
}'

# Chat endpoint
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.1",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}'
```

### Performance Tips for Apple Silicon

1. **Model Selection**:
   - Use quantized models for faster inference (e.g., `llama3.1:8b-instruct-q4_0`)
   - Trade-off: Quality vs Speed vs Memory

2. **Batch Processing**:
   - Process multiple embeddings in single call
   - Reduces overhead vs sequential calls

3. **Context Window Optimization**:
   - Adjust `num_ctx` to minimum required for task
   - Larger context = more memory + slower inference

4. **Multi-threading**:
   - M4 Max has 16 cores (12 performance + 4 efficiency)
   - Set `num_thread` to match available cores (8-12 for balance)

5. **Metal Acceleration**:
   - Automatically enabled on macOS with Apple Silicon
   - No configuration required - native support

---

## 5. CI/CD Integration Best Practices

### Docker Deployment (Linux Only)

**Official Image**: `ollama/ollama` (Docker Hub)

#### Basic Deployment
```bash
docker run -d \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --name ollama \
  ollama/ollama
```

#### GPU-Accelerated (Linux + Nvidia)
```bash
# Requires Nvidia Container Toolkit
docker run -d \
  --gpus=all \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --name ollama \
  ollama/ollama
```

**Important**: macOS Docker deployment NOT recommended - use native installation instead.

### CI/CD Testing Patterns

#### Option 1: Self-Hosted Runner (Recommended for macOS)
```yaml
# .github/workflows/ai-tests.yml
name: AI/ML Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: self-hosted  # macOS runner with Ollama installed

    steps:
      - uses: actions/checkout@v4

      - name: Verify Ollama Service
        run: |
          ollama --version
          ollama list  # Verify models available

      - name: Pull Test Models
        run: |
          ollama pull llama3.1:8b  # Fast model for testing

      - name: Run AI Integration Tests
        run: |
          poetry run pytest tests/integration/ai/ -v
```

#### Option 2: Docker-Based (Linux Runners)
```yaml
# .github/workflows/ai-tests.yml
name: AI/ML Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
        volumes:
          - ollama-data:/root/.ollama

    steps:
      - uses: actions/checkout@v4

      - name: Wait for Ollama to be Ready
        run: |
          timeout 30 bash -c 'until curl -f http://localhost:11434/api/tags; do sleep 1; done'

      - name: Pull Test Models
        run: |
          docker exec ollama ollama pull llama3.1:8b

      - name: Run AI Integration Tests
        env:
          OLLAMA_HOST: http://localhost:11434
        run: |
          poetry run pytest tests/integration/ai/ -v
```

#### Option 3: Mock/Stub for Unit Tests
```python
# tests/unit/services/test_embeddings.py
from unittest.mock import patch, MagicMock
from langchain_ollama import OllamaEmbeddings

def test_embedding_service_call_count():
    with patch('langchain_ollama.OllamaEmbeddings.embed_documents') as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]  # Mock vector

        service = EmbeddingService()
        result = service.embed_texts(["test document"])

        mock_embed.assert_called_once()
        assert len(result[0]) == 3
```

### Testing Strategies

| Strategy | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Self-Hosted Runner** | Real models, accurate behavior | Requires hardware, slower | Integration tests, E2E |
| **Docker Service** | Isolated, reproducible | Linux only, startup time | CI/CD pipelines |
| **Mocks/Stubs** | Fast, no dependencies | Doesn't test real LLM behavior | Unit tests, contract tests |

### Best Practices

1. **Test Model Selection**:
   - Use smaller models for CI (e.g., `llama3.1:8b` vs `llama3.1:405b`)
   - Quantized models for speed (e.g., `q4_0` variants)

2. **Caching**:
   - Cache pulled models between CI runs
   - Use Docker volumes or persistent storage

3. **Timeouts**:
   - Set aggressive timeouts for CI tests (10-30s max)
   - Skip slow tests in pre-commit, run in CI

4. **Environment Parity**:
   - Use same model versions across dev/staging/prod
   - Document model hashes for reproducibility

5. **Cost Optimization**:
   - Avoid cloud-based models in CI (use local Ollama)
   - Limit test dataset size to minimum required

6. **Error Handling**:
   ```python
   from ollama import ResponseError

   try:
       response = chat(model='llama3.1', messages=messages)
   except ResponseError as e:
       if e.status_code == 404:
           logger.error(f"Model not found: {e}")
       elif e.status_code >= 500:
           logger.error(f"Ollama server error: {e}")
       raise
   ```

---

## 6. Implementation Recommendations for SkillForge

### Current Context
- **Platform**: macOS (Apple Silicon M4 Max)
- **Backend**: FastAPI + LangGraph 1.0
- **Testing**: Poetry + pytest
- **CI/CD**: Self-hosted macOS runner

### Integration Plan

#### Phase 1: Local Development Setup
1. Install Ollama via native macOS installer
2. Pull models:
   ```bash
   ollama pull llama3.1:8b      # Fast chat model
   ollama pull nomic-embed-text # Embeddings
   ```
3. Verify installation:
   ```bash
   ollama list
   curl http://localhost:11434/api/tags
   ```

#### Phase 2: Backend Integration
1. Add dependency:
   ```bash
   poetry add langchain-ollama
   ```

2. Create embedding service:
   ```python
   # backend/app/services/embeddings/ollama_service.py
   from langchain_ollama import OllamaEmbeddings
   from app.core.config import settings

   class OllamaEmbeddingService:
       def __init__(self):
           self.embeddings = OllamaEmbeddings(
               model=settings.OLLAMA_EMBEDDING_MODEL,
               base_url=settings.OLLAMA_BASE_URL
           )

       async def embed_texts(self, texts: list[str]) -> list[list[float]]:
           """Generate embeddings for batch of texts"""
           return await self.embeddings.aembed_documents(texts)

       async def embed_query(self, text: str) -> list[float]:
           """Generate embedding for single query"""
           return await self.embeddings.aembed_query(text)
   ```

3. Add configuration:
   ```python
   # backend/app/core/config.py
   class Settings(BaseSettings):
       OLLAMA_BASE_URL: str = "http://localhost:11434"
       OLLAMA_CHAT_MODEL: str = "llama3.1:8b"
       OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
   ```

#### Phase 3: Testing Strategy
1. **Unit Tests** (mocked):
   ```python
   # tests/unit/services/test_ollama_embeddings.py
   @pytest.fixture
   def mock_embeddings(mocker):
       return mocker.patch('langchain_ollama.OllamaEmbeddings')

   def test_embed_texts_batch_size(mock_embeddings):
       service = OllamaEmbeddingService()
       texts = ["doc1", "doc2", "doc3"]

       service.embed_texts(texts)

       mock_embeddings.return_value.aembed_documents.assert_called_once_with(texts)
   ```

2. **Integration Tests** (real Ollama):
   ```python
   # tests/integration/services/test_ollama_integration.py
   import pytest

   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_real_ollama_embedding():
       service = OllamaEmbeddingService()

       vector = await service.embed_query("test document")

       assert isinstance(vector, list)
       assert len(vector) > 0  # Verify embedding dimension
       assert all(isinstance(x, float) for x in vector)
   ```

3. **CI Configuration**:
   ```yaml
   # .github/workflows/backend-tests.yml
   jobs:
     test:
       runs-on: self-hosted  # macOS with Ollama

       steps:
         - name: Verify Ollama
           run: |
             ollama pull nomic-embed-text
             ollama pull llama3.1:8b

         - name: Run Unit Tests (Fast)
           run: poetry run pytest tests/unit/ -v

         - name: Run Integration Tests (Slow)
           run: poetry run pytest tests/integration/ -m integration -v
   ```

#### Phase 4: Performance Optimization
1. **Batch Embeddings**:
   - Process 20-50 documents per batch
   - Monitor memory usage on M4 Max

2. **Caching Strategy**:
   - Cache frequently accessed embeddings
   - Use Redis or in-memory LRU cache

3. **Monitoring**:
   - Track embedding latency (p50/p95/p99)
   - Monitor Ollama memory usage
   - Alert on API errors

---

## 7. Comparison: Ollama vs OpenAI for SkillForge

| Aspect | Ollama (Local) | OpenAI (Cloud) |
|--------|---------------|----------------|
| **Cost** | Free (hardware only) | Pay per token |
| **Latency** | 50-200ms (local) | 200-1000ms (network) |
| **Privacy** | Data never leaves machine | Data sent to OpenAI |
| **Quality** | Good (Llama 3.1 competitive) | Excellent (GPT-4/Claude) |
| **Scalability** | Limited by hardware | Unlimited |
| **Availability** | 100% (local) | 99.9% SLA |
| **Development** | Faster iteration (no API keys) | Production-ready |

**Recommendation for SkillForge**:
- **Development**: Use Ollama (fast iteration, no costs)
- **Production Embeddings**: Ollama (privacy, cost-effective for high volume)
- **Production LLM (Artifacts)**: OpenAI GPT-4 (quality critical for learning materials)

---

## 8. Action Items

### Immediate (Week 1)
- [x] Research Ollama Python integration best practices
- [ ] Install Ollama on development machine
- [ ] Pull test models (llama3.1:8b, nomic-embed-text)
- [ ] Update backend dependencies (poetry add langchain-ollama)

### Short-Term (Week 2-3)
- [ ] Create OllamaEmbeddingService with async support
- [ ] Add unit tests with mocked Ollama client
- [ ] Add integration tests with real Ollama instance
- [ ] Update CI/CD workflow for AI tests

### Long-Term (Month 2+)
- [ ] Benchmark Ollama vs OpenAI embeddings (quality + cost)
- [ ] Implement hybrid strategy (Ollama dev, OpenAI prod)
- [ ] Add monitoring for embedding latency and errors
- [ ] Document Ollama setup in deployment guide

---

## 9. References

### Official Documentation
- Ollama Python Library: https://github.com/ollama/ollama-python
- LangChain Ollama Integration: https://docs.langchain.com/oss/python/integrations/providers/ollama
- Ollama Model Library: https://ollama.com/library
- Ollama Blog - Tool Calling: https://ollama.com/blog/tool-support
- Ollama Blog - Structured Outputs: https://ollama.com/blog/structured-outputs

### Package Versions
- langchain-ollama: 1.0.1 (Latest - December 12, 2025)
- ollama: Latest (pip install ollama)
- Python: 3.10.0+ required

### Best Practice Guides
- Pydantic for JSON schema validation
- Async/await patterns for non-blocking operations
- Batch processing for embeddings (20-50 items)
- Temperature=0 for deterministic structured outputs
- Self-hosted runners for macOS CI/CD

---

**Status**: Research Complete
**Next Step**: Install Ollama and begin Phase 1 implementation
**Blocking Issues**: None
**Dependencies**: Ollama installation (native macOS), langchain-ollama package
