# VA Decision API - Dashboard Guide

## Overview

The VA Decision API includes two comprehensive dashboards for different user personas:

1. **Developer Dashboard** (`/dashboard`) - Real-time monitoring and metrics
2. **Admin Dashboard** (`/admin`) - System management and data administration

## Access URLs

- **API Base**: http://localhost:8001
- **Developer Dashboard**: http://localhost:8001/dashboard
- **Admin Dashboard**: http://localhost:8001/admin
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Developer Dashboard

### Purpose
Real-time monitoring and observability for developers working with the API.

### Key Features

#### 1. Live Metrics Display
- **Total Requests**: Cumulative API request count
- **Average Latency**: Mean response time in milliseconds
- **Success Rate**: Percentage of successful requests
- **Active Connections**: Current WebSocket connections

#### 2. Real-Time Latency Chart
- Line chart showing request response times
- Last 50 data points
- Auto-scrolling as new data arrives
- Color-coded performance indicators:
  - Green: < 100ms (excellent)
  - Yellow: 100-500ms (good)
  - Orange: 500-1000ms (acceptable)
  - Red: > 1000ms (slow)

#### 3. Request Distribution Chart
- Bar chart showing requests by endpoint
- Identifies most-used API routes
- Helps with optimization priorities

#### 4. Recent Requests Table
- Last 20 requests with details:
  - HTTP Method
  - Endpoint path
  - Status code
  - Latency (ms)
  - Timestamp
- Color-coded status (green=2xx, yellow=4xx, red=5xx)

#### 5. Auto-Refresh
- Polls `/metrics` endpoint every 2 seconds
- Live updates without page reload
- Smooth animations and transitions

### Design
- **Theme**: Green/emerald gradient (#10b981 → #059669)
- **Layout**: Grid-based responsive design
- **Charts**: Chart.js for visualizations
- **Background**: Dark theme (#111827)

### Use Cases
- Monitor API performance during development
- Identify slow endpoints
- Track error rates
- Debug latency issues
- Validate optimizations

---

## Admin Dashboard

### Purpose
Comprehensive system management and data administration interface.

### Navigation Sections

#### 1. Overview
- **Dashboard**: System statistics and quick actions
- **Metrics**: Detailed API metrics JSON view

#### 2. Data Management
- **Decisions**: Browse and manage VA decisions
- **Import Data**: Search and import from USA.gov
- **Export Data**: Download data in JSON/CSV/SQL formats

#### 3. System
- **System Logs**: View and filter application logs
- **Database**: Check database status and tables
- **Configuration**: Edit system configuration

#### 4. Tools
- **API Tester**: Test endpoints without external tools
- **Dev Dashboard**: Link to developer dashboard
- **API Docs**: Link to OpenAPI documentation

### Key Features

#### Dashboard (Overview)
**Statistics Cards:**
- Total Decisions count
- Database size (MB)
- API calls in last 24h
- System uptime

**Recent Activity:**
- Timestamped action log
- User tracking
- Status indicators

**Quick Actions:**
- Import decisions
- Run test query
- Check database
- Refresh statistics

#### Decision Management
- **Search**: Filter decisions by case number, outcome, or issues
- **Table View**: Sortable columns with pagination
- **Add Decision**: Modal for manual entry
- **Bulk Operations**: Select and manage multiple decisions

#### Data Import
**Search & Import:**
1. Enter search query (e.g., "tinnitus granted")
2. Select year (2020-2024)
3. Set max results (1-100)
4. Preview results in table
5. Import individual decisions or bulk import

**Features:**
- Integration with USA.gov search API
- Preview before import
- Duplicate detection
- Import status tracking

#### Data Export
**Export Options:**
- **Formats**: JSON, CSV, SQL dump
- **Filters**: All, Granted, Denied, Remanded
- **Download**: Direct to browser

#### System Logs
- **Filtering**: All, Errors, Warnings, Info
- **Refresh**: Manual or auto-refresh
- **Format**: Monospace font, color-coded entries
- **Scrollable**: Max height with overflow

#### Database Management
**Status Display:**
- Connection status
- Host and port
- Database name
- pgvector extension status

**Table Browser:**
- Table name
- Row count
- Size in MB
- Quick actions (View, Query, Export)

#### Configuration Editor
**Editable Settings:**
- Gemini API Key
- PostgreSQL host
- PostgreSQL port
- Database name
- Other environment variables

**Actions:**
- Save configuration
- Reload from .env file
- Restart notification

#### API Tester
**Test Interface:**
1. Select endpoint from dropdown
2. Enter request body (JSON)
3. Send request
4. View response with:
   - Status code
   - Response time
   - Formatted JSON output
   - Error details

**Available Endpoints:**
- GET /health
- GET /metrics
- POST /api/v1/search
- GET /api/v1/decision/{id}
- POST /api/v1/extract

### Design
- **Theme**: Orange/amber gradient (#f59e0b → #d97706)
- **Layout**: Fixed sidebar + main content
- **Navigation**: 12 sections with icons
- **Admin Badge**: Red badge in header
- **Tables**: Sortable, filterable, paginated

### Security Note
⚠️ **Production Warning**: In production environments, protect the `/admin` endpoint with:
- Authentication middleware
- Role-based access control (RBAC)
- IP whitelisting
- Rate limiting
- Audit logging

Current implementation is **open for development only**.

---

## Comparison Matrix

| Feature | Developer Dashboard | Admin Dashboard |
|---------|-------------------|-----------------|
| **Target User** | Developers | System Administrators |
| **Primary Focus** | Monitoring & Metrics | Management & Configuration |
| **Update Frequency** | Real-time (2s) | Manual refresh |
| **Data Visualization** | Charts & Graphs | Tables & Forms |
| **Actions** | Read-only | Create, Update, Delete |
| **Database Access** | No | Yes |
| **Configuration** | No | Yes |
| **API Testing** | Via external tools | Built-in tester |
| **Import/Export** | No | Yes |
| **Color Theme** | Green (emerald) | Orange (amber) |
| **Layout** | Full-width grid | Sidebar navigation |

---

## Usage Workflows

### Developer Workflow
1. Start API server: `python -m uvicorn api.main:app --port 8001`
2. Open developer dashboard: http://localhost:8001/dashboard
3. Monitor metrics while testing
4. Identify slow endpoints
5. Optimize and verify improvements

### Admin Workflow

**Import New Decisions:**
1. Navigate to `/admin`
2. Click "Import Data" in sidebar
3. Enter search query (e.g., "PTSD granted 2024")
4. Preview results
5. Import selected decisions
6. Verify in "Decisions" section

**Export Data:**
1. Click "Export Data" in sidebar
2. Select format (JSON/CSV/SQL)
3. Choose filter (All/Granted/Denied/Remanded)
4. Download file

**Test API Endpoint:**
1. Click "API Tester" in sidebar
2. Select endpoint
3. Enter request body (if POST)
4. Send request
5. Review response

**Monitor Database:**
1. Click "Database" in sidebar
2. View connection status
3. Check table sizes
4. Run queries (coming soon)

---

## Technical Implementation

### Frontend Technologies
- **HTML5**: Semantic markup
- **CSS3**: Grid, Flexbox, animations
- **Vanilla JavaScript**: No dependencies
- **Chart.js**: Data visualization (dev dashboard)
- **Fetch API**: HTTP requests

### Backend Integration
- **FastAPI**: Serves HTML via HTMLResponse
- **Endpoints**: `/dashboard`, `/admin`
- **Data Source**: `/metrics` endpoint
- **CORS**: Enabled for development

### File Locations
```
api/
├── main.py              # FastAPI app with dashboard endpoints
├── dashboard.html       # Developer dashboard
└── admin.html          # Admin dashboard
```

### Dashboard Endpoints
```python
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dev_dashboard():
    """Developer dashboard for real-time monitoring"""
    # Returns dashboard.html

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_dashboard():
    """Admin dashboard for system management"""
    # Returns admin.html
```

---

## Future Enhancements

### Developer Dashboard
- [ ] Historical metrics (7-day, 30-day views)
- [ ] Error rate tracking
- [ ] Token usage visualization
- [ ] Custom metric filters
- [ ] Export metrics as CSV
- [ ] WebSocket for real-time updates
- [ ] Alert thresholds

### Admin Dashboard
- [ ] User authentication (OAuth2)
- [ ] Role-based permissions
- [ ] Audit log viewer
- [ ] Batch operations
- [ ] Scheduled exports
- [ ] Database query builder
- [ ] Configuration backup/restore
- [ ] Email notifications
- [ ] Multi-user support

---

## Troubleshooting

### Dashboard Not Loading
```bash
# Check if server is running
curl http://localhost:8001/health

# Verify dashboard files exist
ls api/dashboard.html api/admin.html

# Check server logs for errors
# Look in terminal where uvicorn is running
```

### Metrics Not Updating
```bash
# Test metrics endpoint directly
curl http://localhost:8001/metrics

# Check browser console for errors
# Open DevTools (F12) → Console tab
```

### 404 Not Found
```bash
# Ensure you're using correct port
# Default is 8001, not 8000

# Verify endpoint registration
curl http://localhost:8001/docs
# Check if /dashboard and /admin appear
```

### CORS Errors
```python
# Verify CORS middleware in main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Best Practices

### Development
1. Keep dashboards open during active development
2. Monitor latency for performance regressions
3. Check error rates after code changes
4. Use admin dashboard for data verification

### Production
1. **Secure admin dashboard** with authentication
2. Set up monitoring alerts
3. Regular metric reviews
4. Backup before bulk operations
5. Rate limit dashboard endpoints

### Performance
1. Adjust auto-refresh intervals based on need
2. Use pagination for large datasets
3. Archive old metrics
4. Optimize database queries

---

## Support

For issues or questions:
1. Check server logs
2. Verify database connection
3. Review API documentation: http://localhost:8001/docs
4. Check GitHub issues: va2ai/va-decision-test

---

**Last Updated**: 2024-01-30
**Version**: 1.0.0
**Author**: VA Decision API Team
