# 🛠️ Setup & Installation Guide

Complete guide to installing, configuring, and running the 52-Week High Tracker.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the App](#running-the-app)
5. [Database Setup](#database-setup)
6. [Troubleshooting](#troubleshooting)
7. [Development Setup](#development-setup)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows, macOS, Linux |
| **Python** | 3.10+ |
| **RAM** | 512MB minimum, 2GB recommended |
| **Disk Space** | 500MB (including dependencies) |
| **Database** | SQLite3 (built-in with Python) |

### Recommended Setup

| Component | Recommended |
|-----------|------------|
| **Python** | 3.11 or 3.12 (latest stable) |
| **RAM** | 4GB+ (for large datasets) |
| **Database** | SQLite3 (or upgrade to PostgreSQL if scaling) |
| **OS** | Ubuntu 20.04+ / macOS 12+ / Windows 10+ |

### Verify Python Installation

```powershell
python --version          # Should be 3.10+
python -m pip --version   # Verify pip is installed
python -m venv --help     # Verify venv support
```

---

## Installation Steps

### Step 1: Clone/Navigate to Project

```powershell
# Navigate to project directory
cd c:\01.My\02.Git\52WeekHighApp

# Or clone from repository (if applicable)
git clone <repo-url>
cd 52WeekHighApp
```

### Step 2: Create Virtual Environment

**Why virtual environment?**
- Isolates project dependencies
- Prevents conflicts with other Python projects
- Makes dependencies reproducible

**Create venv:**

```powershell
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

**Verify activation:**
```powershell
# Prompt should show (venv) prefix
(venv) C:\01.My\02.Git\52WeekHighApp>
```

### Step 3: Upgrade pip

```powershell
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Verify upgrade
pip --version
```

### Step 4: Install Requirements

```powershell
# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Verify installations
pip list
```

**Expected output:**
```
streamlit          1.28.0+
plotly             5.17.0+
pandas             2.0.0+
numpy              1.24.0+
matplotlib         3.7.0+
tabulate           0.9.0+
python-dateutil    2.8.2+
```

### Step 5: Verify Setup

```powershell
# Test Streamlit installation
streamlit --version

# Test Python packages
python -c "import pandas; import streamlit; print('All packages OK')"
```

---

## Configuration

### config.py Settings

All configuration is centralized in `config.py`. Edit to customize:

```python
# Cache TTL (how often database is re-queried)
CACHE_TTL = 3600  # 1 hour (in seconds)

# Change to 1800 for 30 minutes
# Change to 7200 for 2 hours
# Change to 0 to disable caching (NOT RECOMMENDED for performance)

# Table names (if database schema changes)
TABLE_HIGHS = "highs"
TABLE_FIVETOFIFTYCLUB = "fivetofiftyclub"
TABLE_DOWNFROMHIGH = "downfromhigh"

# Plot styling
PLOT_HEIGHT = 600          # Height in pixels
PLOT_COLOR_SCALE = "RdYlGn"  # Color scheme

# Analysis windows
ROLLING_WINDOWS = [7, 30, 60]  # Days for rolling counts
```

### Streamlit Configuration (Optional)

Create `.streamlit/config.toml` for custom settings:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true
toolbarMode = "developer"

[logger]
level = "info"

[server]
port = 8501
headless = true
runOnSave = true
```

### Environment Variables (Optional)

For security-sensitive configurations, use environment variables:

```powershell
# Set environment variable
$env:DB_PATH="C:\path\to\custom\highs.db"

# In Python code:
import os
db_path = os.getenv("DB_PATH", "highs.db")
```

---

## Running the App

### Start the Application

```powershell
# Make sure venv is activated (should see (venv) in prompt)
# Navigate to project directory

# Run Streamlit
streamlit run streamlit_app.py
```

### Expected Output

```
  You can now view your Streamlit app in your browser.

  URL: http://localhost:8501

  Press CTRL+C to quit
```

### Access the App

1. **Automatic:** Browser opens to `http://localhost:8501`
2. **Manual:** Open browser and navigate to `http://localhost:8501`
3. **Remote:** Use `--server.address=0.0.0.0` to allow remote access

### Command Line Options

```powershell
# Run on different port
streamlit run streamlit_app.py --server.port 9000

# Headless mode (no browser auto-open)
streamlit run streamlit_app.py --logger.level=info

# Development mode (reruns on file changes)
streamlit run streamlit_app.py --logger.level=debug
```

### Stop the Application

```powershell
# In terminal where Streamlit is running
Ctrl + C

# Or close the terminal
```

---

## Database Setup

### File Location

Database is stored at project root:
```
c:\01.My\02.Git\52WeekHighApp\highs.db
```

### Database Schema

The application expects these tables:

#### Table 1: `highs`

```sql
CREATE TABLE highs (
    id INTEGER PRIMARY KEY,
    date TEXT,                    -- YYYY-MM-DD
    name TEXT,                    -- Company name
    nse_code TEXT,               -- National Stock Exchange code
    bse_code TEXT,               -- Bombay Stock Exchange code
    market_cap REAL,             -- Current market cap (₹)
    first_market_cap REAL,       -- Market cap at first appearance
    first_seen_date TEXT,        -- Date of first appearance
    industry TEXT,               -- Industry classification
    -- Additional columns as needed
    UNIQUE(date, name)           -- Ensure no duplicates per day
);
```

#### Table 2: `fivetofiftyclub`

```sql
CREATE TABLE fivetofiftyclub (
    id INTEGER PRIMARY KEY,
    date TEXT,
    name TEXT,
    nse_code TEXT,
    bse_code TEXT,
    market_cap REAL,
    industry TEXT,
    correction_pct REAL,         -- Correction % (5-50%)
    UNIQUE(date, name)
);
```

#### Table 3: `downfromhigh`

```sql
CREATE TABLE downfromhigh (
    id INTEGER PRIMARY KEY,
    date TEXT,
    name TEXT,
    nse_code TEXT,
    bse_code TEXT,
    market_cap REAL,
    industry TEXT,
    P_E REAL,                    -- P/E ratio
    P_BV REAL,                   -- P/BV ratio
    correction_pct REAL,         -- Down % (50%+)
    UNIQUE(date, name)
);
```

### Initializing Database

If `highs.db` doesn't exist:

```python
# create_db.py (example script)
import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create tables (SQL above)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS highs (
        date TEXT,
        name TEXT,
        nse_code TEXT,
        bse_code TEXT,
        market_cap REAL,
        industry TEXT,
        PRIMARY KEY (date, name)
    )
""")

conn.commit()
conn.close()
print(f"Database created at {DB_PATH}")
```

### Populating Database

You'll need a data source to populate the database. Examples:

```python
# Insert data from CSV
import pandas as pd
import sqlite3
from config import DB_PATH

df = pd.read_csv("stock_data.csv")
conn = sqlite3.connect(DB_PATH)
df.to_sql("highs", conn, if_exists="append", index=False)
conn.close()
```

### Database Maintenance

```powershell
# Optimize database (run_vacuum.py)
python run_vacuum.py

# Creates: highs.db-wal, highs.db-shm (temporary files, can be deleted)
```

### Backup Database

```powershell
# Create backup
copy highs.db highs.db.backup

# Or use scheduled backup
# (Windows Task Scheduler / cron job)
```

---

## Troubleshooting

### Issue: "No module named 'streamlit'"

**Cause:** Dependencies not installed or venv not activated

**Solution:**
```powershell
# Verify venv is activated (should see (venv) in prompt)
venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt

# Test
streamlit --version
```

### Issue: "ModuleNotFoundError: No module named 'config'"

**Cause:** Running from wrong directory

**Solution:**
```powershell
# Make sure you're in project root
cd c:\01.My\02.Git\52WeekHighApp

# Verify streamlit_app.py exists
dir streamlit_app.py

# Run from project root
streamlit run streamlit_app.py
```

### Issue: "Database error: unable to open database file"

**Cause:** `highs.db` missing or database corrupted

**Solution:**
```powershell
# Check if highs.db exists
Test-Path highs.db

# If missing, create it:
python create_db.py  # (use script above)

# If corrupted, restore from backup:
copy highs.db.backup highs.db

# Or run vacuum to repair:
python run_vacuum.py
```

### Issue: "TypeError: '<' not supported between instances of 'int' and 'str'"

**Cause:** Data type mismatch in styling functions (P/E or P/BV are strings)

**Solution:** Already fixed in code, but ensure `views/03_big_dippers_50pct_plus_down.py` has try-except:
```python
try:
    val = float(val)  # Convert string to numeric
except (ValueError, TypeError):
    return None  # Skip non-convertible values
```

### Issue: App runs slowly

**Solutions:**
1. **Increase cache TTL:**
   ```python
   # In config.py
   CACHE_TTL = 7200  # Increase from 3600 (1 hour to 2 hours)
   ```

2. **Filter by market cap range** (in sidebar)

3. **Select specific industry** instead of all

4. **Clear cache:**
   ```powershell
   streamlit cache clear
   ```

5. **Check database size:**
   ```powershell
   (Get-Item highs.db).Length / 1MB  # Size in MB
   ```

### Issue: Port 8501 already in use

**Solution:**
```powershell
# Use different port
streamlit run streamlit_app.py --server.port 9000

# Or kill process using port 8501
# Windows:
netstat -ano | find ":8501"
taskkill /PID <PID> /F

# Or let Streamlit auto-choose:
streamlit run streamlit_app.py --server.port 0
```

### Issue: Out of Memory errors

**Causes:** Large dataset, memory leaks

**Solutions:**
1. **Upgrade RAM** or reduce dataset
2. **Reduce cache TTL** to free memory sooner
3. **Archive old data** to separate database
4. **Use PostgreSQL** instead of SQLite for large datasets

---

## Development Setup

### Setting Up for Development

```powershell
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install requirements + dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pylint black

# 3. Format code
black streamlit_app.py db_utils.py plot_utils.py views/

# 4. Run linter
pylint streamlit_app.py db_utils.py

# 5. Run tests (if any)
pytest tests/
```

### Project Structure for Development

```
52WeekHighApp/
├── streamlit_app.py          # Main entry point
├── config.py                 # Configuration
├── db_utils.py              # Database operations (edit here for new queries)
├── plot_utils.py            # Visualizations (edit here for new charts)
├── requirements.txt         # Dependencies
├── highs.db                 # Database (created at runtime)
├── views/                   # View modules (add new views here)
│   ├── 01_within_5pct_of_52w_high.py
│   ├── 02_five_to_fifty_pct_from_52w_high.py
│   ├── 03_big_dippers_50pct_plus_down.py
│   ├── trend_shift.py
│   ├── emerging_winners.py
│   ├── trend_analyzer.py
│   ├── industry_tailwinds.py
│   └── momentum_summary.py
├── docs/                    # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── WORKFLOWS.md
│   ├── API_REFERENCE.md
│   └── SETUP.md (this file)
└── tests/                   # Unit tests (if implementing)
    ├── test_db_utils.py
    └── test_plot_utils.py
```

### Adding a New View

1. Create file: `views/my_new_view.py`
2. Implement `main()` function:
   ```python
   import streamlit as st
   from db_utils import get_data_for_date
   
   def main():
       st.title("📊 My New View")
       # Your implementation
   ```

3. Add to navigation in `streamlit_app.py`:
   ```python
   page_options = {
       # ... existing entries
       "📊 My New View": "my_new_view",  # Add this
   }
   ```

4. Test: Select from sidebar navigation

### Code Style Guidelines

```python
# Functions should have docstrings
def my_function(param1: str, param2: int) -> pd.DataFrame:
    """
    Brief description of what function does.
    
    Args:
        param1: Description
        param2: Description
    
    Returns:
        pd.DataFrame: Description of returned data
    """
    pass

# Type hints for clarity
def get_data(date: str) -> pd.DataFrame:
    pass

# Comments for complex logic
if value < vmax:  # Cap value at maximum
    pass
```

### Debugging Tips

```python
# Add print statements (visible in terminal, not in Streamlit)
print("Debug:", my_variable)

# Use st.write() for Streamlit display
st.write("Debug value:", my_variable)

# Use st.dataframe() to inspect data
st.dataframe(df)

# Run in debug mode
streamlit run streamlit_app.py --logger.level=debug
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Database backed up
- [ ] `requirements.txt` version-pinned
- [ ] All views tested
- [ ] No hardcoded secrets in code
- [ ] Error handling in place
- [ ] Cache TTL appropriate
- [ ] Documentation updated

### Deployment Options

1. **Local/On-Premises:**
   ```powershell
   streamlit run streamlit_app.py --server.port 80
   ```

2. **Windows Service:**
   - Use NSSM (Non-Sucking Service Manager)
   - Runs as background service

3. **Docker:**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
   ```

4. **Cloud (Streamlit Cloud, Heroku, AWS):**
   - Push to repository
   - Connect to deployment platform
   - Auto-deploys on push

---

**Last Updated:** March 2026
