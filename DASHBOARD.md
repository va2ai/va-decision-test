# Developer Dashboard

Real-time observability dashboard for the VA Decision Analysis API.

## Access

```bash
# Start the API server
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Open in browser
http://localhost:8001/dashboard
```

## Features

### 📊 Real-Time Metrics

**Total Metrics**: Count of all collected metrics
**Average Latency**: API response time with min/max
**Total Errors**: Error count with category breakdown
**Token Usage**: LLM token consumption for cost tracking

### 📈 Visualizations

**Latency Distribution Chart**
- Rolling 20-point history
- Real-time updates every 3 seconds
- Chart.js powered line graph
- Shows response time trends

### 🎯 Error Categories

Visual display of errors grouped by category:
- `external_api` - Third-party API failures
- `database` - Database errors
- `validation` - Request validation
- `parsing` - Decision parsing failures
- `extraction` - LLM extraction failures
- And more...

### 🌐 API Endpoints

Live statistics for each endpoint:
- Call count
- Average latency
- Status tracking

### 📝 Recent Activity

Real-time log stream showing:
- Request start/completion
- API calls
- Errors with full context
- Structured JSON logs

## Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  VA Decision API Dashboard                          │
│  Real-time observability and telemetry              │
│  ● Healthy                                          │
└─────────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬──────────┐
│ Total    │ Avg      │ Total    │ Token    │
│ Metrics  │ Latency  │ Errors   │ Usage    │
│ 15       │ 234.5ms  │ 2        │ 1523     │
└──────────┴──────────┴──────────┴──────────┘

┌─────────────────────────────────────────────────────┐
│ Latency Distribution                                │
│                                                     │
│  [Chart showing response time over time]            │
│                                                     │
└─────────────────────────────────────────────────────┘

┌────────────────────┬────────────────────────────────┐
│ Error Categories   │ API Endpoints                  │
│                    │                                │
│ external_api: 2    │ GET /health        12 calls    │
│                    │ POST /api/v1/search 3 calls    │
└────────────────────┴────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Recent Activity                    15 events        │
│                                                     │
│ 14:52:03 INFO Dashboard refreshed metrics          │
│ 14:51:58 INFO Request completed: GET /health       │
│ 14:51:45 INFO Fetched decision A24084938           │
│ 14:51:42 ERROR Failed to fetch decision: 404       │
│                                                     │
└─────────────────────────────────────────────────────┘

Auto-refreshing every 3 seconds • Last update: 14:52:03
```

## Design

### Color Scheme

**Dark Theme** optimized for development:
- Background: `#0f172a` (dark slate)
- Cards: `#1e293b` (slate)
- Accents: `#667eea` → `#764ba2` (purple gradient)
- Text: `#e2e8f0` (light slate)
- Success: `#10b981` (green)
- Error: `#ef4444` (red)
- Warning: `#f59e0b` (orange)

### Typography

- Font: System fonts (`-apple-system`, `Segoe UI`, etc.)
- Monospace: `Courier New` for logs and code
- Responsive sizing
- Clear hierarchy

### Layout

- **Grid System**: Responsive CSS Grid
- **Auto-fit**: Adjusts to screen size
- **Minimum card width**: 300px
- **Full-width cards**: For charts and logs
- **Scrollable logs**: Max height 400px

## Auto-Refresh

The dashboard automatically refreshes every **3 seconds**:
- Fetches `/metrics` endpoint
- Updates all visualizations
- Maintains 20-point history
- Shows last update timestamp

## Browser Compatibility

**Tested on:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Requirements:**
- JavaScript enabled
- Modern browser with ES6 support
- Access to CDN for Chart.js

## API Integration

The dashboard consumes these endpoints:

### GET /metrics
Returns current metrics summary:
```json
{
  "total_metrics": 15,
  "latency": {
    "count": 10,
    "avg_ms": 234.5,
    "max_ms": 1523.7,
    "min_ms": 12.4
  },
  "tokens": {
    "total": 45823,
    "count": 23
  },
  "errors": {
    "total": 2,
    "by_category": {
      "external_api": 2
    }
  }
}
```

### GET /logs (Planned)
Will return recent log entries:
```json
{
  "logs": [
    {
      "timestamp": "2026-01-30T14:52:03Z",
      "level": "INFO",
      "message": "Request completed",
      "request_id": "uuid",
      "endpoint": "GET /health"
    }
  ],
  "count": 10
}
```

## Customization

### Change Refresh Interval

Edit `dashboard.html`:
```javascript
// Change from 3000ms (3s) to 5000ms (5s)
setInterval(() => {
    fetchMetrics();
    updateLogs();
}, 5000);  // Changed from 3000
```

### Change History Length

```javascript
// Change from 20 to 50 data points
const MAX_HISTORY = 50;  // Changed from 20
```

### Modify Colors

Update CSS variables in `<style>` section:
```css
:root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --accent-from: #667eea;
    --accent-to: #764ba2;
}
```

## Development Mode

For development with hot reload:

```bash
# Terminal 1: Start API server
cd api
python -m uvicorn main:app --reload --port 8001

# Terminal 2: Open dashboard
open http://localhost:8001/dashboard
```

## Production Deployment

For production, consider:

1. **Serve static dashboard separately**
   - Use nginx/Apache for static files
   - Proxy API requests to FastAPI

2. **Enable CORS properly**
   - Restrict allowed origins
   - Remove wildcard `*`

3. **Add authentication**
   - Protect dashboard endpoint
   - Use API keys or OAuth

4. **Use production metrics backend**
   - Export to Prometheus
   - Send to Datadog/New Relic
   - Store in time-series database

## Metrics Export

To export metrics for external monitoring:

```python
# In api/main.py
@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Export metrics in Prometheus format."""
    return PlainTextResponse(
        generate_prometheus_format(metrics.get_summary())
    )
```

## Troubleshooting

### Dashboard Shows No Data

**Issue**: Metrics show all zeros

**Solution**:
1. Make API calls to generate metrics
2. Check `/metrics` endpoint returns data
3. Verify browser console for errors

### Auto-Refresh Not Working

**Issue**: Dashboard doesn't update

**Solution**:
1. Check browser console for fetch errors
2. Verify API server is running
3. Check CORS configuration

### Chart Not Rendering

**Issue**: Latency chart is blank

**Solution**:
1. Verify Chart.js CDN loads
2. Check browser console
3. Ensure data format is correct

### Port Conflict

**Issue**: Server won't start on port 8001

**Solution**:
```bash
# Find process using port
netstat -ano | findstr :8001

# Kill process (Windows)
taskkill /PID <pid> /F

# Or use different port
uvicorn main:app --port 8002
```

## Future Enhancements

- [ ] Live log streaming with WebSockets
- [ ] Historical metrics with date range picker
- [ ] Exportable reports (PDF, CSV)
- [ ] Alert configuration UI
- [ ] Custom metric dashboards
- [ ] Performance profiling integration
- [ ] Cost tracking dashboard
- [ ] SLA/uptime monitoring

## Screenshots

Access the live dashboard at `http://localhost:8001/dashboard` to see:

- **Real-time metrics** updating every 3 seconds
- **Interactive charts** showing latency trends
- **Color-coded logs** with timestamps and levels
- **Error categories** with visual tags
- **Endpoint statistics** with call counts

---

**Pro Tip**: Keep the dashboard open in a second monitor while developing to monitor API performance in real-time!
