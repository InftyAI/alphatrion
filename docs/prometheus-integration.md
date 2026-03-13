# Prometheus Push Gateway Integration

AlphaTrion supports automatic export of OpenTelemetry span metrics to Prometheus via push gateway. This allows you to monitor LLM token usage, latency, and other metrics from your experiments.

## Overview

When enabled, AlphaTrion automatically:
- Extracts metrics from LLM spans (token counts, duration, model usage)
- Pushes metrics to a Prometheus push gateway
- Labels metrics with team_id, experiment_id, run_id, and model

## Setup

### 1. Start Infrastructure

The complete monitoring stack (push gateway, Prometheus, Grafana) is included in docker-compose:

```bash
make up
```

This starts:
- **Push Gateway**: `http://localhost:9091` - Receives metrics from experiments
- **Prometheus**: `http://localhost:9090` - Scrapes metrics from push gateway
- **Grafana**: `http://localhost:3000` - Visualizes metrics (admin/admin)

### 2. Enable Prometheus Export

Set environment variables in your `.env` file:

```bash
# Enable tracing (required for spans)
ALPHATRION_ENABLE_TRACING=true

# Enable Prometheus export
ALPHATRION_ENABLE_PROMETHEUS=true

# Push gateway URL (default: localhost:9091)
ALPHATRION_PROMETHEUS_PUSHGATEWAY_URL=localhost:9091

# Job name for metrics (default: alphatrion)
ALPHATRION_PROMETHEUS_JOB_NAME=alphatrion
```

### 3. Run Your Experiment

Metrics are automatically pushed when your application makes LLM calls:

```python
import alphatrion as alpha
from alphatrion import experiment

alpha.init(user_id="<your_user_id>")

async def my_task():
    # Your LLM calls here - metrics are automatically captured
    # and pushed to Prometheus
    pass

async with experiment.CraftExperiment.start(name="my_experiment") as exp:
    task = exp.run(my_task)
    await task.wait()
```

## Available Metrics

### LLM Token Metrics

- **`alphatrion_llm_tokens_total`** - Total LLM tokens consumed
  - Labels: `team_id`, `experiment_id`, `model`, `token_type` (input/output/total)

- **`alphatrion_llm_input_tokens_total`** - Total input tokens
  - Labels: `team_id`, `experiment_id`, `model`

- **`alphatrion_llm_output_tokens_total`** - Total output tokens
  - Labels: `team_id`, `experiment_id`, `model`

### LLM Request Metrics

- **`alphatrion_llm_requests_total`** - Total number of LLM requests
  - Labels: `team_id`, `experiment_id`, `model`, `status`

- **`alphatrion_llm_duration_seconds`** - LLM request duration histogram
  - Labels: `team_id`, `experiment_id`, `model`
  - Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s

### Error Tracking

- **`alphatrion_llm_errors_total`** - Total LLM errors by type
  - Labels: `team_id`, `error_type`
  - Error types: `timeout`, `rate_limit`, `auth_error`, `invalid_request`, `connection_error`, `server_error`, `unknown`

## Metrics Philosophy

The Prometheus integration focuses exclusively on **LLM metrics** (token usage, request counts, latency) as these are the most critical for monitoring and alerting in GenAI applications.

General span metrics are intentionally excluded because:
- Without semantic classification, they would mix different operation types
- You already have LLM-specific metrics which are more actionable
- For detailed trace analysis, use the ClickHouse trace store which supports high-cardinality queries

This keeps your Prometheus metrics clean, performant, and focused on what matters most.

## Viewing Metrics

### View Push Gateway Metrics

Check metrics in the push gateway:

```bash
curl http://localhost:9091/metrics
```

### Example Prometheus Queries

Total tokens by model:
```promql
sum by (model) (alphatrion_llm_tokens_total{token_type="total"})
```

Request rate per experiment:
```promql
rate(alphatrion_llm_requests_total[5m])
```

Average LLM duration by model:
```promql
rate(alphatrion_llm_duration_seconds_sum[5m]) / rate(alphatrion_llm_duration_seconds_count[5m])
```

P95 LLM latency:
```promql
histogram_quantile(0.95, alphatrion_llm_duration_seconds_bucket)
```

## Using Grafana

### Access Grafana

1. Open `http://localhost:3000`
2. Login with credentials: `admin` / `admin`
3. Navigate to the **"AlphaTrion - Platform Dashboard"**

### Dashboard Overview

The platform dashboard provides a comprehensive view combining operational health and cost tracking:

**Platform-Wide Stats (Top Row):**
- **Total Platform Tokens** - Aggregate token consumption across all teams/experiments
- **Total Platform Requests** - Total API calls made
- **Error Rate** - Real-time error percentage
- **Unique Teams/Experiments** - Count of distinct teams and experiments

**Cost & Usage Breakdown:**
- **Top 10 Teams by Token Usage** - Bar chart showing highest consumers (anonymized)
- **Top 10 Experiments by Token Usage** - Bar chart for cost tracking per experiment (anonymized)
- **Token Usage (Cumulative)** - Platform-wide token growth over time
- **Input vs Output Tokens** - Platform-wide token type breakdown

**Model & Error Analytics:**
- **Requests by Model** - Pie chart of model distribution
- **Tokens by Model** - Token consumption by model
- **Errors by Type** - Error classification breakdown

**Performance:**
- **LLM Latency (P50, P95)** - Response time percentiles by model

### Custom Queries

Create your own panels with queries like:

```promql
# Token usage by experiment
sum by (experiment_id) (alphatrion_llm_tokens_total{token_type="total"})

# Request rate per team
rate(alphatrion_llm_requests_total{team_id="YOUR_TEAM_ID"}[5m])

# Average latency
rate(alphatrion_llm_duration_seconds_sum[5m]) / rate(alphatrion_llm_duration_seconds_count[5m])

# Success rate
sum(rate(alphatrion_llm_requests_total{status="OK"}[5m])) / sum(rate(alphatrion_llm_requests_total[5m]))

# Top 5 teams by token usage
topk(5, sum by (team_id) (alphatrion_llm_tokens_total{token_type="total"}))

# Errors by team
sum by (team_id) (alphatrion_llm_errors_total)

# Count unique experiments (derived metric)
count(sum by (experiment_id) (alphatrion_llm_requests_total))

# Count unique teams (derived metric)
count(sum by (team_id) (alphatrion_llm_requests_total))
```

## Production Considerations

### Push Gateway URL

For production, configure the push gateway URL to point to your infrastructure:

```bash
ALPHATRION_PROMETHEUS_PUSHGATEWAY_URL=pushgateway.prod.example.com:9091
```

### Grouping Keys

You can customize grouping keys by modifying `PrometheusSpanProcessor` initialization in your code:

```python
from alphatrion.tracing.prometheus_span_processor import PrometheusSpanProcessor

processor = PrometheusSpanProcessor(
    pushgateway_url="localhost:9091",
    job_name="my-app",
    grouping_key={"instance": "app-1", "environment": "production"}
)
```

### Label Cardinality

The implementation is optimized for low cardinality to ensure Prometheus performance. Metrics are aggregated by:

- `team_id` - Organization/team level
- `experiment_id` - Experiment level
- `model` - AI model being used (LLM metrics only)
- Other minimal dimensions (`status`, `token_type`)

Labels like `run_id`, `span_kind`, and `semantic_kind` are intentionally excluded. For detailed trace analysis and span classification, use the ClickHouse trace store which is optimized for high-cardinality data.

## Troubleshooting

### Metrics not appearing

1. Check tracing is enabled:
   ```bash
   ALPHATRION_ENABLE_TRACING=true
   ```

2. Check Prometheus is enabled:
   ```bash
   ALPHATRION_ENABLE_PROMETHEUS=true
   ```

3. Verify push gateway is running:
   ```bash
   curl http://localhost:9091/metrics
   ```

4. Check logs for errors:
   ```bash
   # Look for "PrometheusSpanProcessor" in logs
   ```

### Push gateway connection errors

- Ensure push gateway URL is correct
- Check network connectivity
- Verify firewall rules allow connections
