# Admin Dashboard

Comprehensive administrative interface for the VA Decision Analysis API.

## Access

```bash
# Admin Dashboard
http://localhost:8001/admin

# Developer Dashboard
http://localhost:8001/dashboard

# API Documentation
http://localhost:8001/docs
```

## Overview

The admin dashboard provides full system management capabilities with a professional sidebar navigation interface.

### Security Warning

⚠️ **Production Deployment**: The `/admin` endpoint is currently unprotected. In production, implement authentication:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "admin" or credentials.password != "secret":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username

@app.get("/admin", dependencies=[Depends(verify_admin)])
async def get_admin_dashboard():
    ...
```

## Dashboard Sections

### 1. 📊 Dashboard (Overview)

**Statistics Cards:**
- **Total Decisions**: Count of decisions in database
- **Database Size**: PostgreSQL + pgvector storage
- **API Calls (24h)**: Recent API usage
- **System Uptime**: Service health status

**Recent Activity Log:**
- Timestamp
- Action performed
- User (when auth is implemented)
- Status

**Quick Actions:**
- Import Decisions
- Run Test Query
- Check Database
- Refresh Stats

Auto-refreshes every 5 seconds.

---

### 2. 📈 Metrics

Real-time system metrics in JSON format:
- Latency statistics
- Token usage
- Error counts by category
- Total metrics collected

Same data as `/metrics` endpoint but formatted for readability.

---

### 3. 📄 Decision Management

**Features:**
- Search decisions by case number
- View decision list with pagination
- Filter by outcome (Granted/Denied/Remanded)
- Add decisions manually
- View decision details

**Table Columns:**
- Case Number
- Date
- Outcome (color-coded badges)
- Issue Count
- Actions (View/Edit/Delete)

**Search:**
- Real-time search filtering
- Case number lookup
- Content search

---

### 4. 📥 Import Data

Import decisions from USA.gov search:

**Fields:**
- Search Query (e.g., "tinnitus granted")
- Year (2020-2024)
- Max Results (1-100)

**Workflow:**
1. Enter search criteria
2. Click "Search & Preview"
3. Review results in table
4. Click "Import" for each decision
5. System fetches, parses, and ingests

**Preview Table:**
- Case Number
- Year
- Import Button

Integrates with `/api/v1/search` and `/api/v1/ingest` endpoints.

---

### 5. 📤 Export Data

Export decisions in multiple formats:

**Export Formats:**
- **JSON**: Complete structured data
- **CSV**: Spreadsheet-compatible
- **SQL Dump**: Database backup

**Data Selection:**
- All Decisions
- Granted Only
- Denied Only
- Remanded Only

**Coming Soon:**
- Custom field selection
- Date range filtering
- Compressed archives

---

### 6. 📝 System Logs

Real-time log viewer with filtering:

**Features:**
- Log level filtering (All/Error/Warning/Info)
- Scrollable log viewer
- Refresh button
- Structured JSON logs

**Log Display:**
- Timestamp
- Level (color-coded)
- Message
- Request ID
- Metadata

**Filters:**
- All Levels
- Errors Only
- Warnings Only
- Info Only

---

### 7. 💾 Database

Database status and management:

**Connection Status:**
- PostgreSQL host and port
- Database name
- Connection health

**Tables View:**
- Table name
- Row count
- Size in MB
- Actions (View/Optimize)

**Tables:**
- `decisions` - Core decision data
- `issues` - Extracted issues
- `evidence` - Evidence mentions
- `passages` - Key text passages
- `authorities` - Legal citations

---

### 8. ⚙️ Configuration

System configuration editor:

**Settings:**
- Gemini API Key (password field)
- PostgreSQL Host
- PostgreSQL Port
- Database Name
- Database User/Password

**Actions:**
- Save Configuration
- Reload from .env
- Test Connections

⚠️ **Warning**: Configuration changes require server restart.

**Security:**
- API keys shown as passwords
- Validation before saving
- Backup .env before changes

---

### 9. 🔧 API Tester

Interactive API endpoint tester:

**Features:**
- Endpoint selector (all API routes)
- Request body editor (JSON)
- Send request button
- Response viewer with syntax highlighting

**Endpoints:**
- GET /health
- GET /metrics
- POST /api/v1/search
- GET /api/v1/decision/{id}
- POST /api/v1/extract
- And all others...

**Request Body:**
- JSON text area
- Syntax validation
- Auto-formatting

**Response Display:**
- HTTP status code
- Response headers
- JSON body (formatted)
- Error messages

---

## Navigation Sidebar

### Overview
- 📊 Dashboard
- 📈 Metrics

### Data Management
- 📄 Decisions
- 📥 Import Data
- 📤 Export Data

### System
- 📝 System Logs
- 💾 Database
- ⚙️ Configuration

### Tools
- 🔧 API Tester
- 📊 Dev Dashboard (opens in new tab)
- 📚 API Docs (opens in new tab)

---

## Design & UI

### Color Scheme

**Orange/Amber Theme** (admin authority):
- Header Gradient: `#f59e0b` → `#d97706`
- Background: `#111827` (dark slate)
- Sidebar: `#1f2937` (darker slate)
- Cards: `#1f2937` with `#374151` borders
- Text: `#f3f4f6` (light)
- Accents: Orange for admin actions

### Layout

**Fixed Sidebar** (260px):
- Always visible
- Scrollable sections
- Active state highlighting
- Icon + text navigation

**Main Content Area**:
- Left margin: 260px
- Responsive padding
- Full-height layout
- Scrollable content

### Typography

- System fonts for native feel
- Monospace for code/logs
- Clear hierarchy
- Readable sizes

### Components

**Cards**: Rounded, shadowed containers
**Tables**: Striped, hoverable rows
**Buttons**: Color-coded by action type
**Modals**: Centered dialogs
**Forms**: Labeled inputs with validation
**Badges**: Status indicators

---

## Common Tasks

### Import 10 Decisions

1. Click "📥 Import Data" in sidebar
2. Enter query: "tinnitus granted"
3. Select year: 2024
4. Max results: 10
5. Click "Search & Preview"
6. Click "Import" for each result

### Export All Granted Decisions

1. Click "📤 Export Data"
2. Format: JSON
3. Selection: Granted Only
4. Click "Download Export"

### Check Database Health

1. Click "💾 Database"
2. View connection status
3. Review table sizes
4. Check row counts

### Test API Endpoint

1. Click "🔧 API Tester"
2. Select endpoint
3. Enter request body (if POST)
4. Click "Send Request"
5. View response

### View Recent Errors

1. Click "📝 System Logs"
2. Filter: Errors Only
3. Click "Refresh Logs"
4. Review error entries

---

## API Integration

The admin dashboard uses these endpoints:

### Core Endpoints
- `GET /metrics` - System metrics
- `GET /health` - Health check
- `GET /logs` - Log entries (planned)

### Data Endpoints
- `POST /api/v1/search` - Search decisions
- `POST /api/v1/ingest` - Import decision
- `GET /api/v1/decision/{id}` - Fetch decision

### Future Endpoints
- `GET /admin/stats` - Admin-specific stats
- `POST /admin/export` - Data export
- `GET /admin/users` - User management
- `POST /admin/config` - Update configuration

---

## Browser Compatibility

**Tested:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Requirements:**
- JavaScript enabled
- Modern browser with CSS Grid
- Minimum 1280px width recommended

---

## Development

### Add New Section

1. Add navigation item in sidebar:
```html
<div class="nav-item" onclick="showSection('my-section')">
    <span class="nav-icon">🔥</span> My Section
</div>
```

2. Add content section:
```html
<div id="my-section" class="content-section">
    <div class="card">
        <h2>My Section</h2>
        <!-- Content here -->
    </div>
</div>
```

3. Add section logic in JavaScript:
```javascript
if (sectionId === 'my-section') {
    loadMySection();
}
```

### Customize Colors

Update CSS variables:
```css
/* Change header gradient */
background: linear-gradient(135deg, #yourColor1, #yourColor2);

/* Change sidebar background */
.sidebar {
    background: #yourColor;
}
```

### Add Modal

```html
<div id="myModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2>Title</h2>
            <button class="modal-close" onclick="closeModal('myModal')">&times;</button>
        </div>
        <!-- Content -->
    </div>
</div>
```

---

## Production Deployment

### Security Checklist

- [ ] Implement authentication (OAuth2, JWT, Basic Auth)
- [ ] Add role-based access control (RBAC)
- [ ] Enable HTTPS only
- [ ] Set secure CORS policy
- [ ] Add rate limiting
- [ ] Implement audit logging
- [ ] Encrypt sensitive configuration
- [ ] Add session timeout
- [ ] Enable CSRF protection
- [ ] Validate all inputs

### Authentication Example

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify token
    user = verify_token(token)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@app.get("/admin", dependencies=[Depends(get_current_user)])
async def admin_dashboard():
    ...
```

### Reverse Proxy

```nginx
# Nginx configuration
location /admin {
    auth_basic "Admin Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8001/admin;
}
```

---

## Troubleshooting

### Admin Dashboard Not Loading

**Issue**: 404 Not Found

**Solutions**:
1. Check server is running
2. Verify `admin.html` exists in `api/` directory
3. Check server logs for errors
4. Try restarting server without `--reload`

### Cannot Import Decisions

**Issue**: Import button does nothing

**Solutions**:
1. Check console for JavaScript errors
2. Verify `/api/v1/ingest` endpoint works
3. Check Gemini API key is set
4. Verify database connection

### Database Section Empty

**Issue**: Tables not showing

**Solutions**:
1. Verify PostgreSQL is running
2. Check database connection string
3. Ensure tables exist
4. Check user permissions

---

## Future Enhancements

- [ ] User management (create/edit/delete users)
- [ ] Role-based permissions
- [ ] Scheduled imports/exports
- [ ] Bulk operations
- [ ] Data validation rules
- [ ] Backup/restore functionality
- [ ] Performance monitoring
- [ ] Alert configuration
- [ ] Webhook management
- [ ] API key management
- [ ] Audit log viewer
- [ ] System health checks

---

## Comparison: Dev vs Admin Dashboard

| Feature | Dev Dashboard | Admin Dashboard |
|---------|--------------|-----------------|
| **Purpose** | Development monitoring | System management |
| **Theme** | Purple gradient | Orange/amber |
| **Layout** | Full-width cards | Sidebar navigation |
| **Focus** | Metrics & logs | Data & config |
| **Auto-refresh** | 3 seconds | 5 seconds |
| **Sections** | 6 | 12 |
| **User** | Developers | Administrators |
| **Security** | Public | Should be protected |

---

**Access both dashboards:**

- Dev Dashboard: `http://localhost:8001/dashboard`
- Admin Dashboard: `http://localhost:8001/admin`
- API Docs: `http://localhost:8001/docs`

Perfect for full-stack development and production management! 🚀
