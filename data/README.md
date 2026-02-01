# Data Directory

This directory contains runtime data for the QCU News Scraper.

## Contents

| File/Folder | Description |
|-------------|-------------|
| `cache.sqlite` | Local SQLite database for duplicate detection |
| `scraper_state.json` | Checkpoint file for failure recovery |
| `logs/` | Log files (rotated daily) |
| `.lock` | Lock file to prevent multiple instances |

## ⚠️ Important

- This directory is **gitignored** (except this README)
- Do not manually edit `scraper_state.json` unless necessary
- Logs older than 30 days are automatically deleted

## Troubleshooting

### Reset Scraper State
```bash
rm data/scraper_state.json
```

### Clear Duplicate Cache
```bash
rm data/cache.sqlite
```

### View Recent Logs
```bash
# Windows
type data\logs\scraper_YYYY-MM-DD.log

# macOS/Linux
cat data/logs/scraper_YYYY-MM-DD.log
```
