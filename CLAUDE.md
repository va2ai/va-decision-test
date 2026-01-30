# VA Decision API - Project Documentation

## Overview
FastAPI-based semantic search API for VA Board of Veterans' Appeals decisions. Uses Google Gemini for embeddings and PostgreSQL with pgvector for similarity search.

## Quick Start
```bash
# Start server
python -m uvicorn api.main:app --port 8001

# Access dashboards
http://localhost:8001/dashboard  # Developer monitoring
http://localhost:8001/admin      # System administration
http://localhost:8001/docs       # API documentation
```

## Project Structure
```
va-decision-test/
├── api/
│   ├── main.py              # FastAPI application
│   ├── dashboard.html       # Developer dashboard (green theme)
│   ├── admin.html          # Admin dashboard (orange theme)
│   ├── db.py               # Database connection & pgvector
│   ├── models.py           # Pydantic models
│   ├── usa_search.py       # USA.gov search integration
│   ├── decision_parser.py  # PDF text extraction
│   └── gemini_client.py    # Google Gemini embeddings
├── scripts/
│   ├── setup_db.py         # Database initialization
│   └── test_*.py           # Test scripts
├── DASHBOARD_GUIDE.md      # Comprehensive dashboard docs
└── README.md               # Main documentation
```

## Current Features

### API Endpoints
- `GET /health` - Health check
- `GET /metrics` - Performance metrics
- `POST /api/v1/search` - Semantic search
- `GET /api/v1/decision/{case_number}` - Get decision by case
- `POST /api/v1/ingest` - Import decision from USA.gov
- `POST /api/v1/extract` - Extract text from PDF

### Developer Dashboard (`/dashboard`)
- Real-time latency monitoring
- Request distribution charts
- Recent requests table
- Auto-refresh every 2 seconds
- Chart.js visualizations
- Green/emerald theme

### Admin Dashboard (`/admin`)
- Decision management (browse, search, add)
- Data import from USA.gov search
- Data export (JSON, CSV, SQL)
- System logs viewer
- Database status & table browser
- Configuration editor
- API endpoint tester
- Orange/amber theme with sidebar nav

## Database Schema

### decisions table
```sql
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(20) UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    decision_date DATE,
    outcome VARCHAR(50),
    full_text TEXT,
    summary TEXT,
    embedding vector(768),  -- Gemini text-embedding-004
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### issues table
```sql
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id),
    issue_text TEXT NOT NULL,
    outcome VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Configuration

### Environment Variables (.env)
```bash
GEMINI_API_KEY=your_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=va_decisions
DB_USER=postgres
DB_PASSWORD=your_password
```

### Required Dependencies
- fastapi
- uvicorn
- psycopg2-binary
- google-generativeai
- python-dotenv
- requests
- pypdf

## Development Workflow

### Starting Development
```bash
# 1. Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Start PostgreSQL
# Ensure PostgreSQL with pgvector extension is running

# 3. Initialize database (first time only)
python scripts/setup_db.py

# 4. Start API server
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8001/health

# Metrics
curl http://localhost:8001/metrics

# Search
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "tinnitus service connected", "top_k": 5}'

# Import decision
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"case_number": "A24084938", "year": 2024}'
```

## Dashboard Features

### Developer Dashboard
**Purpose:** Real-time API monitoring for developers

**Key Metrics:**
- Total requests processed
- Average latency (ms)
- Success rate (%)
- Active connections

**Visualizations:**
- Line chart: Latency over time (last 50 requests)
- Bar chart: Request distribution by endpoint
- Table: Recent requests with status codes

**Auto-refresh:** Every 2 seconds from `/metrics` endpoint

### Admin Dashboard
**Purpose:** System administration and data management

**Sections:**
1. Dashboard - Statistics and quick actions
2. Metrics - Detailed JSON metrics view
3. Decisions - Browse and manage decisions
4. Import Data - Search and import from USA.gov
5. Export Data - Download in JSON/CSV/SQL
6. System Logs - View application logs
7. Database - Check status and tables
8. Configuration - Edit environment settings
9. API Tester - Test endpoints interactively

**Security Note:** Protect `/admin` with auth in production!

## Git Workflow

### Commit and Deploy
```bash
# Add changes
git add .

# Commit with detailed message
git commit -m "feat: description"

# Push to trigger GCP deploy
git push origin master
```

### Active Git Worktrees
- None currently active

## Known Issues & Solutions

### Port Already in Use
```bash
# Find process on port 8001
netstat -ano | findstr :8001

# Kill process (Windows PowerShell)
Stop-Process -Id <PID> -Force

# Kill process (Linux/Mac)
kill -9 <PID>
```

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify credentials in .env
# Ensure pgvector extension is installed
```

### Embeddings API Error
```bash
# Verify Gemini API key
echo $GEMINI_API_KEY

# Check API quota
# Gemini has rate limits - add exponential backoff
```

## Performance Considerations

### Current Metrics (as of 2024-01-30)
- Total API calls: 170+
- Average latency: ~9ms
- Max latency: ~1376ms
- Min latency: ~0.4ms

### Optimization Opportunities
1. Add connection pooling for database
2. Cache embeddings for common queries
3. Implement request rate limiting
4. Add Redis for session/cache management
5. Use async database operations
6. Batch embedding generation

## Testing

### Manual Testing
- Use `/admin` API Tester
- Use developer dashboard for monitoring
- Check `/docs` for OpenAPI interface

### Automated Testing (TODO)
- [ ] Unit tests for models
- [ ] Integration tests for API endpoints
- [ ] Load testing with locust
- [ ] Database migration tests

## Deployment

### Local Development
- Uses uvicorn with --reload
- Port: 8001
- Host: 127.0.0.1

### Production (GCP Cloud Run)
- Auto-deploys on `git push origin master`
- Uses Cloud SQL for PostgreSQL
- Environment variables from Secret Manager
- HTTPS with custom domain

## Future Enhancements

### High Priority
- [ ] User authentication for admin dashboard
- [ ] Role-based access control (RBAC)
- [ ] Audit logging for admin actions
- [ ] Batch decision import
- [ ] Advanced search filters
- [ ] Historical metrics storage

### Medium Priority
- [ ] Email notifications
- [ ] Scheduled data exports
- [ ] Custom metric alerts
- [ ] Database query builder
- [ ] Configuration backup/restore
- [ ] Multi-user support

### Low Priority
- [ ] Dark/light theme toggle
- [ ] Custom dashboard widgets
- [ ] Export metrics as CSV
- [ ] WebSocket for real-time updates
- [ ] Mobile-responsive admin UI

## Maintenance Tasks

### Daily
- Monitor error rates in dev dashboard
- Check database size
- Review system logs

### Weekly
- Backup database
- Review API metrics
- Update dependencies

### Monthly
- Analyze query performance
- Clean up old logs
- Review and update documentation

## Support & Resources

- **Documentation:** See DASHBOARD_GUIDE.md
- **API Docs:** http://localhost:8001/docs
- **GitHub:** va2ai/va-decision-test
- **Issues:** Report bugs via GitHub Issues

## Recent Changes

### 2024-01-30
- ✅ Added comprehensive admin dashboard
- ✅ Added developer dashboard with real-time metrics
- ✅ Created DASHBOARD_GUIDE.md
- ✅ Fixed health endpoint
- ✅ Added metrics tracking
- ✅ Implemented pgvector similarity search

## Notes

- Always update this file after significant changes
- Commit and push after every deploy
- Use descriptive commit messages
- Never commit .env files
- Test locally before pushing to master
