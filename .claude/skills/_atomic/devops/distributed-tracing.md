---
name: distributed-tracing
description: OpenTelemetry distributed tracing
version: 1.0.0
tags: [tracing, opentelemetry, observability]
size: atomic
domain: devops
---

# Distributed Tracing

## OpenTelemetry Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
```

## Creating Spans

```python
# Parent span
with tracer.start_as_current_span("analyze_content") as span:
    span.set_attribute("content.url", url)

    # Child span
    with tracer.start_as_current_span("fetch_content") as fetch_span:
        content = await fetch_url(url)
        fetch_span.set_attribute("content.size", len(content))

    # Another child
    with tracer.start_as_current_span("generate_embedding"):
        embedding = await embed_text(content)
```

## Parallel Spans

```python
async def analyze_with_span(agent: str, content: str):
    with tracer.start_as_current_span(f"agent_{agent}"):
        return await agent.analyze(content)

results = await asyncio.gather(
    analyze_with_span("tech_comparator", content),
    analyze_with_span("security_auditor", content)
)
```

## Sampling

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
```

**Strategies**:
- Development: 100%
- Production: 10% normal, 100% errors

## Trace Analysis

```
duration > 2s          # Slow traces
status = error         # Error traces
service.name = "api"   # Specific service
user.id = "abc-123"    # Specific user
```
