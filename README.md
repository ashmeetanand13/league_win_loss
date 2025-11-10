European Football Streaks Tracker
A Streamlit web application that tracks winning and losing streaks across European football leagues by scraping live data from FBref.
Features

Multi-League Support: Covers 30+ European leagues (Big 5 + others)
Real-time Scraping: Fetches latest match results from FBref.com
Streak Detection: Identifies teams on consecutive win/loss runs
Customizable Thresholds: Set custom streak lengths (1-10 games)
xG Analytics: Displays expected goals data when available
Smart Caching: 1-hour cache to minimize API calls and avoid rate limits
Debug Mode: Test individual leagues and troubleshoot scraping issues

Tech Stack

Streamlit for web interface
BeautifulSoup for web scraping
Pandas for data manipulation
Requests for HTTP calls

Usage
Run streamlit run app.py to launch the dashboard. The app respects FBref's rate limits with built-in delays and caching.

Note
Includes rate limit handling (429 errors) with user guidance for retry strategies.
