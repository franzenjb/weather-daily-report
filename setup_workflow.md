# Setting Up GitHub Actions Workflow

Since we can't push workflow files directly with our current authentication, you'll need to add the workflow manually:

## Steps:

1. Go to your repository: https://github.com/franzenjb/weather-daily-report

2. Click on "Actions" tab

3. Click "New workflow" or "Set up a workflow yourself"

4. Copy and paste this workflow code:

```yaml
name: Weather Daily Report

on:
  schedule:
    # Runs at 10:15 UTC every day (6:15 AM ET)
    - cron: "15 10 * * *"
  workflow_dispatch:  # Allows manual triggering
  push:
    branches: [main]  # Run on push to main for testing

jobs:
  generate-report:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run weather report generator
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python run.py
      
      - name: Commit and push changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/summary.html output/summary.html data/ || true
          git commit -m "Update weather report - $(date -u +'%Y-%m-%d %H:%M UTC')" || echo "No changes to commit"
          git push || echo "No changes to push"
```

5. Name the file: `.github/workflows/weather.yml`

6. Click "Commit new file"

## Add API Keys (if needed):

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add `OPENAI_API_KEY` if your weather script uses OpenAI

## Test the workflow:

1. Go to Actions tab
2. Find "Weather Daily Report" workflow
3. Click "Run workflow" to test manually

The workflow will also run automatically every day at 10:15 UTC!