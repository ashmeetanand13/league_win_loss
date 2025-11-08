import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Football Streaks Tracker", layout="wide")

st.title("⚽ European Football - Streaks Tracker")

# League mapping - START WITH BIG 5 TO AVOID RATE LIMITS
LEAGUES = {
     # Big 5
    "Premier League": 9,
    "La Liga": 12,
    "Serie A": 11,
    "Bundesliga": 20,
    "Ligue 1": 13,
    
    # Next Tier
    "Eredivisie": 23,                    # Netherlands
    "Primeira Liga": 32,                  # Portugal
    "Belgian Pro League": 37,             # Belgium
    "Scottish Premiership": 40,           # Scotland
    "Championship": 10,                   # England 2nd
    
    # Additional Major Leagues
    "Süper Lig": 26,                     # Turkey
    "Austrian Bundesliga": 38,            # Austria
    "Swiss Super League": 46,             # Switzerland
    "Greek Super League": 27,             # Greece
    "Danish Superliga": 50,               # Denmark
    "Swedish Allsvenskan": 29,            # Sweden
    "Norwegian Eliteserien": 28,          # Norway
    "Ukrainian Premier League": 39,       # Ukraine
    "Polish Ekstraklasa": 36,             # Poland
    "Czech First League": 63,             # Czech Republic
    
    # Smaller Leagues (if available)
    "Croatian First Football League": 64, # Croatia
    "Serbian SuperLiga": 65,              # Serbia
    "Romanian Liga I": 62,                # Romania
    "Bulgarian First League": 68,         # Bulgaria
    "Hungarian NB I": 66,                 # Hungary
    "Slovenian PrvaLiga": 70,             # Slovenia
    "Slovak Super Liga": 69,              # Slovakia
}



@st.cache_data(ttl=3600)
def scrape_league(league_name, delay=3):
    """Scrape matches from FBref using dynamic column detection"""
    league_id = LEAGUES[league_name]
    url = f"https://fbref.com/en/comps/{league_id}/schedule/"
    
    try:
        # Add delay to respect rate limits
        time.sleep(delay)
        
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        if response.status_code == 429:
            st.warning(f"⚠️ {league_name}: Rate limited! Wait 5 minutes and try again.")
            return pd.DataFrame()
        
        if response.status_code != 200:
            st.warning(f"⚠️ {league_name}: HTTP {response.status_code}")
            return pd.DataFrame()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        div = soup.find('div', {'id': lambda x: x and x.startswith('div_sched_')})
        if not div:
            st.warning(f"⚠️ {league_name}: No schedule div found (ID: {league_id})")
            return pd.DataFrame()
        
        table = div.find('table')
        if not table:
            st.warning(f"⚠️ {league_name}: No table in div")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ {league_name}: {str(e)}")
        return pd.DataFrame()
    
    # Get header row to map column names to indices
    thead = table.find('thead')
    if not thead:
        return pd.DataFrame()
    
    header_row = thead.find_all('tr')[-1]  # Get last row of header (actual column names)
    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    
    # Find column indices dynamically
    col_map = {header: idx for idx, header in enumerate(headers)}
    
    # Required columns
    date_idx = col_map.get('Date')
    home_idx = col_map.get('Home')
    score_idx = col_map.get('Score')
    away_idx = col_map.get('Away')
    
    # Optional xG columns (they may not always be present)
    # Find xG columns - usually there are two, one before Score and one after
    xg_indices = [idx for idx, h in enumerate(headers) if h == 'xG']
    home_xg_idx = xg_indices[0] if len(xg_indices) >= 1 else None
    away_xg_idx = xg_indices[1] if len(xg_indices) >= 2 else None
    
    if None in [date_idx, home_idx, score_idx, away_idx]:
        return pd.DataFrame()
    
    matches = []
    tbody = table.find('tbody')
    rows = tbody.find_all('tr')
    
    for row in rows:
        if 'spacer' in row.get('class', []):
            continue
            
        cols = row.find_all(['th', 'td'])
        if len(cols) <= max(date_idx, home_idx, score_idx, away_idx):
            continue
        
        try:
            date = cols[date_idx].get_text(strip=True)
            home_team = cols[home_idx].get_text(strip=True)
            score = cols[score_idx].get_text(strip=True)
            away_team = cols[away_idx].get_text(strip=True)
            
            # Get xG values if available
            home_xg = cols[home_xg_idx].get_text(strip=True) if home_xg_idx and len(cols) > home_xg_idx else ''
            away_xg = cols[away_xg_idx].get_text(strip=True) if away_xg_idx and len(cols) > away_xg_idx else ''
            
            if not score or ('–' not in score and '-' not in score):
                continue
            
            if '–' in score:
                home_score, away_score = score.split('–')
            else:
                home_score, away_score = score.split('-')
            
            home_score = int(home_score.strip())
            away_score = int(away_score.strip())
            
            matches.append({
                'league_name': league_name,
                'league_id': league_id,
                'date': date,
                'home_team': home_team,
                'home_xg': home_xg,
                'away_team': away_team,
                'away_xg': away_xg,
                'home_score': home_score,
                'away_score': away_score,
                'score': score
            })
        except (ValueError, IndexError):
            continue
    
    return pd.DataFrame(matches)

def get_team_results(df, team_name):
    """Get all results for a team in chronological order"""
    home_games = df[df['home_team'] == team_name].copy()
    home_games['opponent'] = home_games['away_team']
    home_games['team_score'] = home_games['home_score']
    home_games['opp_score'] = home_games['away_score']
    home_games['team_xg'] = home_games['home_xg']
    home_games['opp_xg'] = home_games['away_xg']
    home_games['location'] = 'H'
    
    away_games = df[df['away_team'] == team_name].copy()
    away_games['opponent'] = away_games['home_team']
    away_games['team_score'] = away_games['away_score']
    away_games['opp_score'] = away_games['home_score']
    away_games['team_xg'] = away_games['away_xg']
    away_games['opp_xg'] = away_games['home_xg']
    away_games['location'] = 'A'
    
    all_games = pd.concat([home_games, away_games])
    all_games = all_games.sort_values('date', ascending=False)
    
    # Determine result
    all_games['result'] = all_games.apply(
        lambda x: 'W' if x['team_score'] > x['opp_score'] 
        else ('L' if x['team_score'] < x['opp_score'] else 'D'), 
        axis=1
    )
    
    return all_games[['date', 'opponent', 'location', 'team_score', 'opp_score', 'team_xg', 'opp_xg', 'result', 'league_name', 'league_id']]

def find_game_streaks(df, win_streak_count=3, loss_streak_count=3):
    """Find teams with specified consecutive wins or losses"""
    teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
    
    win_streaks = []
    loss_streaks = []
    
    for team in teams:
        results = get_team_results(df, team)
        
        if len(results) < max(win_streak_count, loss_streak_count):
            continue
        
        # Check for win streak
        if len(results) >= win_streak_count:
            last_wins = results.head(win_streak_count)
            results_str = ''.join(last_wins['result'].tolist())
            
            if results_str == 'W' * win_streak_count:
                win_streaks.append({
                    'team': team,
                    'league_name': last_wins.iloc[0]['league_name'],
                    'league_id': last_wins.iloc[0]['league_id'],
                    'games': last_wins
                })
        
        # Check for loss streak
        if len(results) >= loss_streak_count:
            last_losses = results.head(loss_streak_count)
            results_str = ''.join(last_losses['result'].tolist())
            
            if results_str == 'L' * loss_streak_count:
                loss_streaks.append({
                    'team': team,
                    'league_name': last_losses.iloc[0]['league_name'],
                    'league_id': last_losses.iloc[0]['league_id'],
                    'games': last_losses
                })
    
    return win_streaks, loss_streaks

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    st.subheader("📊 Streak Configuration")
    win_streak = st.number_input("Winning Streak Length", min_value=1, max_value=10, value=3)
    loss_streak = st.number_input("Losing Streak Length", min_value=1, max_value=10, value=3)
    
    st.markdown("---")
    
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.subheader("🔧 Debug Mode")
    
    test_league = st.selectbox("Test single league:", list(LEAGUES.keys()))
    if st.button("Test Scraper"):
        with st.spinner(f"Testing {test_league}..."):
            league_id = LEAGUES[test_league]
            url = f"https://fbref.com/en/comps/{league_id}/schedule/"
            st.code(f"URL: {url}")
            
            try:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                st.write(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    divs = soup.find_all('div', {'id': lambda x: x and 'sched' in str(x)})
                    st.write(f"Found {len(divs)} schedule divs:")
                    for div in divs[:3]:
                        st.code(div.get('id'))
                else:
                    st.error("Failed to load page")
            except Exception as e:
                st.error(f"Error: {e}")

# Main app
st.info(f"📊 Scraping data from FBref.com - Looking for {win_streak}-game win streaks and {loss_streak}-game loss streaks")

# Scrape all leagues
with st.spinner("Scraping leagues..."):
    all_matches = []
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    start_time = time.time()
    
    for idx, league_name in enumerate(LEAGUES.keys()):
        status_placeholder.text(f"Scraping {league_name}... ({idx+1}/{len(LEAGUES)})")
        df_league = scrape_league(league_name)
        
        if not df_league.empty:
            all_matches.append(df_league)
            st.success(f"✅ {league_name}: {len(df_league)} matches")
        else:
            st.error(f"❌ {league_name}: No data")
            
        progress_bar.progress((idx + 1) / len(LEAGUES))
    
    elapsed = time.time() - start_time
    progress_bar.empty()
    status_placeholder.empty()
    st.success(f"✅ Scraping completed in {elapsed:.1f} seconds")

if all_matches:
    df_all = pd.concat(all_matches, ignore_index=True)
    st.success(f"✅ Loaded {len(df_all)} matches from {len(all_matches)} leagues")
    
    # League selector
    st.subheader("Select League")
    selected_league = st.selectbox(
        "Filter by league:",
        ["All Leagues"] + list(df_all['league_name'].unique())
    )
    
    # Filter data
    if selected_league == "All Leagues":
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all['league_name'] == selected_league]
    
    st.markdown("---")
    
    # Find streaks
    with st.spinner("Analyzing streaks..."):
        win_streaks, loss_streaks = find_game_streaks(df_filtered, win_streak, loss_streak)
    
    # Display results in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🔥 Teams with {win_streak} Consecutive Wins")
        if win_streaks:
            for item in win_streaks:
                with st.expander(f"**{item['team']}** ({item['league_name']})"):
                    games_df = item['games'][['date', 'opponent', 'location', 'team_score', 'opp_score', 'team_xg', 'opp_xg', 'result']]
                    games_df.columns = ['Date', 'Opponent', 'H/A', 'Score', 'Opp', 'xG', 'Opp xG', 'Result']
                    st.table(games_df)
        else:
            st.info(f"No teams with exactly {win_streak} consecutive wins")
    
    with col2:
        st.subheader(f"📉 Teams with {loss_streak} Consecutive Losses")
        if loss_streaks:
            for item in loss_streaks:
                with st.expander(f"**{item['team']}** ({item['league_name']})"):
                    games_df = item['games'][['date', 'opponent', 'location', 'team_score', 'opp_score', 'team_xg', 'opp_xg', 'result']]
                    games_df.columns = ['Date', 'Opponent', 'H/A', 'Score', 'Opp', 'xG', 'Opp xG', 'Result']
                    st.table(games_df)
        else:
            st.info(f"No teams with exactly {loss_streak} consecutive losses")
    
    # Summary stats
    st.markdown("---")
    st.subheader("📊 Summary")
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric(f"Teams on {win_streak}-Win Streak", len(win_streaks))
    col_stat2.metric(f"Teams on {loss_streak}-Loss Streak", len(loss_streaks))
    
else:
    st.error("❌ No data scraped from any league")
    st.warning("""
    **⚠️ RATE LIMITED (Status 429)**
    
    FBref is blocking requests because you're scraping too fast.
    
    **Solutions:**
    1. **Wait 5-10 minutes** before trying again
    2. Clear cache (sidebar button) and refresh
    3. Test one league at a time using Debug Mode
    4. Don't refresh the page multiple times quickly
    
    **Why this happens:**
    - FBref limits requests to prevent abuse
    - Cached data lasts 1 hour to reduce requests
    - First run always takes longer (15-20 seconds for Big 5)
    """)