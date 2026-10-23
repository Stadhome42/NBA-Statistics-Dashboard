import time
import pandas as pd
import plotly.express as px
import streamlit as st
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, playercareerstats

st.title("👤 Player Statistics & Performance Analytics")

# ==========================================
# 1. SIDEBAR SEARCH & DYNAMIC SEASON FETCHING
# ==========================================
st.sidebar.header("Player Search Controls")

player_name_query = st.sidebar.text_input(
    "Search Player Name", 
    value="Cooper Flagg",
    help="Type any active or historical NBA player's full name"
)

# Helper function to get player info & their active career seasons
@st.cache_data(ttl=86400)
def get_player_career_seasons(search_query):
    found = players.find_players_by_full_name(search_query)
    if not found:
        return None, None, []
    
    player_info = found[0]
    player_id = player_info['id']
    official_name = player_info['full_name']
    
    # Pull career stats to find all active seasons for this player
    time.sleep(0.4)
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        df_career = career.get_data_frames()[0]  # SeasonTotalsRegularSeason
        
        if not df_career.empty:
            # Extract unique season IDs (e.g., '2003-04', '2004-05', ..., '2024-25')
            player_seasons = df_career['SEASON_ID'].unique().tolist()
            # Sort in descending order (most recent first)
            player_seasons = sorted(player_seasons, reverse=True)
        else:
            player_seasons = []
    except Exception:
        player_seasons = []
        
    return player_info, official_name, player_seasons

player_info, full_name, available_seasons = get_player_career_seasons(player_name_query)

if player_info is None:
    st.error(f"❌ Player '{player_name_query}' not found. Please check spelling.")
    st.stop()

if not available_seasons:
    st.warning(f"No career season records found for **{full_name}**.")
    st.stop()

# Dynamic Dropdown Options adapted to this specific player
season_options = ["All Time"] + available_seasons
selected_season = st.sidebar.selectbox(
    f"Select Season ({len(available_seasons)} Seasons Active)", 
    season_options, 
    index=0
)

# ==========================================
# 2. CACHED API GAMELOG FETCHING
# ==========================================
@st.cache_data(ttl=3600)
def fetch_player_gamelog_fast(player_id, season_choice):
    try:
        print(f"Fetching game logs for player ID {player_id} for season '{season_choice}'...")
        # 1. Single API Call: Fetch ALL career games at once using season='ALL'
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='ALL')
        df_all_games = gamelog.get_data_frames()[0]
        
        if df_all_games.empty:
            return pd.DataFrame()
            
        df_all_games['GAME_DATE'] = pd.to_datetime(df_all_games['GAME_DATE'])
        df_all_games = df_all_games.sort_values('GAME_DATE').reset_index(drop=True)

        # Derive Season Year column (e.g. '2023-24') locally in Pandas
        df_all_games['Season Start Year'] = (df_all_games['GAME_DATE'] - pd.DateOffset(months=6)).dt.year
        df_all_games['Season Year'] = df_all_games['Season Start Year'].apply(lambda x: f"{x}-{str(x + 1)[-2:]}")

        # 2. Filter locally in Pandas instead of making new API calls
        if season_choice != "All Time":
            df_filtered = df_all_games[df_all_games['Season Year'] == season_choice].copy()
        else:
            df_filtered = df_all_games.copy()

        return df_filtered

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# ==========================================
# 3. MAIN CONTENT CONTAINER (CLEAR ON LOAD)
# ==========================================
main_page_area = st.empty()

if player_name_query:
    main_page_area.empty()

    with st.spinner(f"Fetching game logs for {full_name} ({selected_season})..."):
        df_player = fetch_player_gamelog_fast(player_info['id'], selected_season)

    with main_page_area.container():
        if df_player is None or df_player.empty:
            st.warning(f"No recorded game logs found for **{full_name}** in season **{selected_season}**.")
            st.stop()

        # Header Summary
        st.subheader(f"📊 {full_name} — {selected_season} Performance Overview")

        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("Points / Game", f"{df_player['PTS'].mean():.1f}")
        m_col2.metric("Rebounds / Game", f"{df_player['REB'].mean():.1f}")
        m_col3.metric("Assists / Game", f"{df_player['AST'].mean():.1f}")
        m_col4.metric("FG Percentage", f"{(df_player['FG_PCT'].mean() * 100):.1f}%")
        m_col5.metric("Total Games Played", len(df_player))

        st.markdown("---")

        # Chart Controls & Visualizations
        available_metrics = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FG3_PCT', 'PLUS_MINUS']
        metric_labels = {
            'PTS': 'Points',
            'REB': 'Rebounds',
            'AST': 'Assists',
            'STL': 'Steals',
            'BLK': 'Blocks',
            'TOV': 'Turnovers',
            'FG_PCT': 'Field Goal %',
            'FG3_PCT': '3-Point FG %',
            'PLUS_MINUS': 'Plus / Minus'
        }
        st.sidebar.subheader("Statistics Controls")
        selected_metric = st.sidebar.selectbox(
            "Select Statistic to Chart", 
            available_metrics, 
            index=0,
            format_func=lambda x: metric_labels.get(x, x)
        )

        rolling_window = st.sidebar.slider("Rolling Window (Games)", min_value=1, max_value=20, value=5)

        # Derive Season Year column for grouping and distinct line colors
        df_player['Season Start Year'] = (df_player['GAME_DATE'] - pd.DateOffset(months=6)).dt.year
        df_player['Season Year'] = df_player['Season Start Year'].apply(lambda x: f"{x}-{str(x + 1)[-2:]}")

        # Calculate rolling moving average grouped per season
        df_player['ROLLING_STAT'] = df_player.groupby('Season Year')[selected_metric].transform(
            lambda x: x.rolling(window=rolling_window, min_periods=1).mean()
        )

        # Plotly Line Chart with distinct colors and line breaks per season
        fig_player = px.line(
            df_player,
            x='GAME_DATE',
            y='ROLLING_STAT',
            color='Season Year',  # <--- SEPARATES COLOR & BREAKS LINES PER SEASON
            title=f"{full_name}: {rolling_window}-Game Moving Average ({metric_labels.get(selected_metric, selected_metric)}) — {selected_season}",
            labels={
                'GAME_DATE': 'Game Date',
                'ROLLING_STAT': f'{metric_labels.get(selected_metric, selected_metric)} ({rolling_window}-Game Moving Avg)',
                'Season Year': 'Season'
            },
            hover_data=['MATCHUP', 'WL', selected_metric],
            template="plotly_dark",
            markers=True
        )

        fig_player.update_traces(marker=dict(size=4))
        st.plotly_chart(fig_player, width='stretch')

        # Raw Game Logs Dataframe
        with st.expander(f"📋 View Raw Game Logs for {full_name} ({selected_season})"):
            cols_to_show = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FG3_PCT']
            existing_cols = [c for c in cols_to_show if c in df_player.columns]
            st.dataframe(df_player[existing_cols].sort_values('GAME_DATE', ascending=False), width='stretch')