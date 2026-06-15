# Monitoring & Logging Guide

This guide covers the monitoring and logging infrastructure for Developer Memory AI.

## Overview

The application includes:
- **Structured Logging**: Winston-based logging with daily rotation
- **Performance Metrics**: Custom metrics collection and reporting
- **Error Tracking**: Sentry integration (optional)
- **Health Checks**: Endpoint for monitoring service health
- **Request Logging**: Automatic API request logging

## Logging

### Log Levels

- `error`: Error messages and exceptions
- `warn`: Warning messages
- `info`: General information (default)
- `http`: HTTP request logs
- `debug`: Detailed debugging information

### Configuration

Set log level via environment variable:

```bash
LOG_LEVEL=debug  # error, warn, info, http, debug
```

### File Logging

Enable file logging:

```bash
LOG_TO_FILE=true
LOG_DIR=logs
```

Log files are automatically rotated daily and kept for:
- Error logs: 14 days
- Combined logs: 14 days
- HTTP logs: 7 days

### Usage

```typescript
import { logInfo, logError, logWarn, logDebug } from '@/lib/logger';

// Simple logging
logInfo('User logged in');
logError('Database connection failed', error);

// With context
logInfo('Indexing started', {
  repositoryId: 'proj_123',
  filesCount: 150
});

// Specialized logging
import { logApiRequest, logIndexing, logCache } from '@/lib/logger';

logApiRequest('POST', '/api/projects/select', 200, 45);
logIndexing('proj_123', 75, 'src/index.ts');
logCache(true, 'search:proj_123:query');
```

## Performance Metrics

### Collecting Metrics

```typescript
import { metrics, Timer, measure } from '@/lib/metrics';

// Manual timing
const timer = new Timer('database.query');
// ... do work
timer.stop();

// Automatic timing
const result = await measure('api.search', async () => {
  return await performSearch();
});

// Record custom metric
metrics.record('embeddings.generated', 1, { model: 'gemini' });
```

### Viewing Metrics

Access metrics endpoint:

```bash
curl http://localhost:3000/api/metrics \
  -H "Authorization: Bearer your_admin_key"
```

Response:

```json
{
  "timestamp": "2024-01-01T00:00:00.000Z",
  "uptime": {
    "seconds": 3600,
    "formatted": "1h 0m 0s"
  },
  "memory": {
    "rss": 134217728,
    "heapUsed": 67108864,
    "formatted": {
      "rss": "128.00 MB",
      "heapUsed": "64.00 MB"
    }
  },
  "performance": {
    "api.search": {
      "count": 100,
      "avg": 45.2,
      "p50": 42,
      "p95": 78,
      "p99": 95
    }
  },
  "cache": {
    "embeddings": { "size": 150 },
    "search": { "size": 50 }
  }
}
```

### System Metrics

Automatic collection every 60 seconds:

```typescript
import { startMetricsCollection } from '@/lib/metrics';

// Start collection (in server startup)
startMetricsCollection(60000); // 60 seconds
```

## Error Tracking (Sentry)

### Setup

1. Create Sentry account and project
2. Get DSN from project settings
3. Add to environment:

```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
```

### Usage

Errors are automatically captured. Manual capture:

```typescript
import * as Sentry from '@sentry/nextjs';

try {
  // ... code
} catch (error) {
  Sentry.captureException(error, {
    tags: {
      component: 'indexer',
      repositoryId: 'proj_123'
    },
    extra: {
      filesProcessed: 50
    }
  });
}
```

### Custom Events

```typescript
Sentry.captureMessage('Indexing completed', {
  level: 'info',
  tags: { repositoryId: 'proj_123' }
});
```

## Health Checks

### Endpoint

```bash
GET /api/health
```

Response (healthy):

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "database": "connected"
}
```

Response (unhealthy):

```json
{
  "status": "unhealthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "database": "disconnected",
  "error": "Connection timeout"
}
```

### Monitoring Services

Configure with:
- **UptimeRobot**: Free tier, 5-minute checks
- **Pingdom**: Advanced monitoring
- **StatusCake**: Global monitoring

Example UptimeRobot setup:
- URL: `https://your-app.com/api/health`
- Interval: 5 minutes
- Alert: Email/SMS on failure

## Request Logging

Automatic logging via middleware for all API requests:

```
2024-01-01 12:00:00 http: POST /api/projects/select 201 45ms
```

Includes:
- Request ID (X-Request-ID header)
- Method and path
- Status code
- Duration
- User agent
- IP address

## Dashboard Integration

### Grafana

Create dashboard with:

1. **System Metrics Panel**:
   - Memory usage
   - CPU usage
   - Uptime

2. **Performance Panel**:
   - API response times (p50, p95, p99)
   - Request rate
   - Error rate

3. **Cache Panel**:
   - Hit rate
   - Size
   - Evictions

### Prometheus

Export metrics in Prometheus format:

```typescript
// Add to src/app/api/metrics/prometheus/route.ts
export async function GET() {
  const summary = metrics.getSummary();
  
  let output = '';
  for (const [name, stats] of Object.entries(summary)) {
    output += `# TYPE ${name}_avg gauge\n`;
    output += `${name}_avg ${stats.avg}\n`;
    output += `# TYPE ${name}_p95 gauge\n`;
    output += `${name}_p95 ${stats.p95}\n`;
  }
  
  return new Response(output, {
    headers: { 'Content-Type': 'text/plain' }
  });
}
```

## Alerting

### Email Alerts

Configure in production:

```typescript
import { logError } from '@/lib/logger';
import nodemailer from 'nodemailer';

const transporter = nodemailer.createTransport({
  // ... config
});

// On critical error
if (error.critical) {
  await transporter.sendMail({
    to: 'admin@example.com',
    subject: 'Critical Error in Developer Memory AI',
    text: error.message
  });
}
```

### Slack Alerts

```typescript
import { IncomingWebhook } from '@slack/webhook';

const webhook = new IncomingWebhook(process.env.SLACK_WEBHOOK_URL);

await webhook.send({
  text: `Error in ${component}: ${error.message}`
});
```

## Log Analysis

### Search Logs

```bash
# Find errors
grep "error" logs/combined-2024-01-01.log

# Find slow requests
grep "POST /api/search" logs/http-2024-01-01.log | awk '$NF > 1000'

# Count requests by endpoint
grep "POST" logs/http-2024-01-01.log | awk '{print $3}' | sort | uniq -c
```

### Log Aggregation

Use tools like:
- **Loki**: Grafana's log aggregation
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Datadog**: Cloud-based monitoring

## Performance Optimization

### Identify Slow Operations

```typescript
import { metrics } from '@/lib/metrics';

// Get slowest operations
const summary = metrics.getSummary();
const slow = Object.entries(summary)
  .filter(([_, stats]) => stats.p95 > 1000)
  .sort((a, b) => b[1].p95 - a[1].p95);

console.log('Slowest operations:', slow);
```

### Memory Leaks

Monitor memory growth:

```bash
# Check memory over time
curl http://localhost:3000/api/metrics | jq '.memory.heapUsed'
```

If memory grows continuously, investigate:
- Cache size limits
- Event listener cleanup
- Database connection pooling

## Best Practices

1. **Log Levels**:
   - Production: `info` or `warn`
   - Development: `debug`
   - Never log sensitive data (passwords, tokens)

2. **Metrics**:
   - Keep metric names consistent
   - Use tags for dimensions
   - Don't create too many unique metrics

3. **Error Tracking**:
   - Add context to errors
   - Use breadcrumbs for debugging
   - Filter out noise (404s, health checks)

4. **Performance**:
   - Monitor p95 and p99, not just averages
   - Set SLOs (Service Level Objectives)
   - Alert on SLO violations

5. **Costs**:
   - Sentry: Free tier 5k events/month
   - Log storage: Rotate and compress
   - Metrics: Sample high-volume metrics

## Troubleshooting

### High Memory Usage

```typescript
// Force garbage collection (development only)
if (global.gc) {
  global.gc();
}

// Check heap snapshot
const v8 = require('v8');
const snapshot = v8.writeHeapSnapshot();
console.log('Heap snapshot:', snapshot);
```

### Slow Requests

```typescript
// Add detailed timing
const timer = new Timer('api.search.detailed');
const step1 = Date.now();
await fetchFromDB();
console.log('DB fetch:', Date.now() - step1);

const step2 = Date.now();
await generateEmbeddings();
console.log('Embeddings:', Date.now() - step2);

timer.stop();
```

### Missing Logs

Check:
1. Log level is appropriate
2. File permissions (if LOG_TO_FILE=true)
3. Disk space
4. Log directory exists

## Production Checklist

- [ ] Set LOG_LEVEL to `info` or `warn`
- [ ] Enable LOG_TO_FILE
- [ ] Configure log rotation
- [ ] Set up Sentry (optional)
- [ ] Configure health check monitoring
- [ ] Set up alerting
- [ ] Create monitoring dashboard
- [ ] Test error reporting
- [ ] Document runbooks
- [ ] Set up log aggregation (optional)

## Support

- Documentation: https://docs.devmemory.ai
- GitHub Issues: https://github.com/yourusername/developer-memory-ai/issues
