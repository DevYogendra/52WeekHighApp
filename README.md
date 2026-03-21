# 📊 52-Week High Tracker

A Streamlit-based financial analysis application that tracks and analyzes Indian company stocks reaching their 52-week highs. Provides multiple perspectives on market momentum, valuation trends, and sector performance.

## 🎯 Overview

This application helps investors and analysts:
- **Track stocks** near their 52-week highs
- **Analyze momentum shifts** week-over-week
- **Identify trends** in company performance
- **Monitor industry tailwinds** and sector rotations
- **Discover emerging winners** among midcap stocks
- **Visualize trends** with interactive charts

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- SQLite3 database (`highs.db`)

### Installation

1. **Clone/Navigate to project:**
```bash
cd 52WeekHighApp
```

2. **Create virtual environment (recommended):**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`

## 📁 Project Structure

```
52WeekHighApp/
├── streamlit_app.py          # Main entry point & navigation
├── config.py                 # Configuration constants
├── db_utils.py              # Database utilities & queries
├── plot_utils.py            # Chart & visualization helpers
├── requirements.txt         # Python dependencies
├── highs.db                 # SQLite database
├── views/                   # Page modules
│   ├── near_52w_high_view.py
│   ├── pullback_candidates_view.py
│   ├── deep_dippers_view.py
│   ├── trend_shift_view.py
│   ├── emerging_winners_view.py
│   ├── trend_analyzer_view.py
│   ├── industry_tailwinds_view.py
│   └── momentum_summary_view.py
└── docs/                    # Documentation
    ├── ARCHITECTURE.md
    ├── WORKFLOWS.md
    ├── API_REFERENCE.md
    └── SETUP.md
```

## 📖 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and component overview
- **[WORKFLOWS.md](docs/WORKFLOWS.md)** - Detailed workflows for each view
- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Function documentation
- **[SETUP.md](docs/SETUP.md)** - Installation and configuration guide

## 🔑 Key Features

### 1. **Within 5% of 52W High**
Stocks trading within 5% of their 52-week highs—potential breakout candidates.

### 2. **5–50% from 52W High**
Stocks that have corrected 5-50%—balance between correction and recovery potential.

### 3. **Big Dippers (50%+ Down)**
Stocks down 50%+—deep value or distressed situations.

### 4. **Trend Shift Analyzer**
Week-over-week momentum changes across stocks and industries.

### 5. **Emerging Winners**
Stocks with accelerating positive momentum and rising valuations.

### 6. **Trend Analyzer**
Long-term trend analysis with market cap evolution and valuation metrics.

### 7. **Industry Tailwinds**
Sector-level analysis of momentum and performance trends.

### 8. **Momentum Summary**
Snapshot of which stocks appear most frequently in 52-week highs across rolling windows (7, 30, 60 days).

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **Backend** | Python 3.10+ |
| **Database** | SQLite3 |
| **Data Processing** | Pandas, NumPy |
| **Visualization** | Plotly, Matplotlib |
| **Date Handling** | python-dateutil |

## 📊 Database Schema

### Main Tables

- **highs** - Daily 52-week high occurrences
- **fivetofiftyclub** - Stocks in 5-50% correction range
- **downfromhigh** - Stocks down 50%+

### Key Columns
- `name` - Company name
- `nse_code` - NSE listing code
- `bse_code` - BSE listing code
- `date` - Data date
- `market_cap` - Market capitalization (₹ in crores)
- `industry` - Industry classification

## ⚙️ Configuration

Edit `config.py` to customize:

```python
CACHE_TTL = 3600              # Cache refresh interval (seconds)
TABLE_HIGHS = "highs"         # Main data table name
PLOT_HEIGHT = 600             # Chart height (pixels)
PLOT_COLOR_SCALE = "RdYlGn"   # Chart color scheme
ROLLING_WINDOWS = [7, 30, 60] # Analysis periods (days)
```

## 🔗 External Links

- **Screener.in** - Used for company detail pages
- NSE/BSE codes link directly to screener profiles

## 🐛 Troubleshooting

### App crashes with "Database error"
- Ensure `highs.db` exists in project root
- Verify SQLite3 is installed
- Check database file permissions

### Charts not rendering
- Clear Streamlit cache: `streamlit cache clear`
- Verify Plotly installation: `pip install --upgrade plotly`

### Slow performance
- Cache TTL is 1 hour—wait or clear cache if data is stale
- Try filtering by market cap range or industry
- Reduce date range in views

## 📝 Contributing

To add new views:
1. Create file in `views/` folder with `.py` extension
2. Implement `main()` function
3. Add to navigation in `streamlit_app.py`
4. Document in `WORKFLOWS.md`

## 📄 License

[Specify your license here]

## 👤 Author

[Your name/organization]

---

**Last Updated:** March 2026
