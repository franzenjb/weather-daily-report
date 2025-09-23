# Weather Daily Report

Automated weather report generator that fetches weather data and creates HTML reports.

## Features
- Fetches weather data from multiple sources
- Generates comprehensive HTML reports
- Runs automatically via GitHub Actions
- Publishes reports to GitHub Pages

## Structure
- `src/` - Source code modules
- `data/` - Temporary data storage
- `output/` - Generated reports
- `docs/` - GitHub Pages content
- `style/` - CSS and styling
- `template/` - HTML templates

## GitHub Actions Setup
This project runs automatically every day at 10:15 UTC using GitHub Actions.

## Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables in `.env`
3. Run: `python run.py`

## Live Report

https://franzenjb.github.io/weather-daily-report/summary.html