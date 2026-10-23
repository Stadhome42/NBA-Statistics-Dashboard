import os
import glob
import time
import pandas as pd
import streamlit as st
from nba_api.stats.static import teams
from nba_api.stats.endpoints import teamgamelogs

# Set global page config for the app
st.set_page_config(page_title="NBA Stats Hub", page_icon="🏀", layout="wide")

# ==========================================
# 1. DATA EXTRACTION FUNCTIONS
# ==========================================
def download_all_teams_basic_stats_master_csvs(start_year=2015, end_year=2025, output_dir="nba_basic_master_csvs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    seasons = [f"{year}-{str(year + 1)[-2:]}" for year in range(start_year, end_year + 1)]
    all_teams = teams.get_teams()
    for idx, team in enumerate(all_teams, start=1):
        clean_name = team['full_name'].replace(" ", "_")
        filename = os.path.join(output_dir, f"basic_{clean_name}_{start_year}_{end_year + 1}.csv")
        if os.path.exists(filename):
            continue
        team_games_list = []
        for season in seasons:
            try:
                basic_logs = teamgamelogs.TeamGameLogs(
                    team_id_nullable=team['id'],
                    season_nullable=season,
                    measure_type_player_game_logs_nullable='Base'
                )
                df_season = basic_logs.get_data_frames()[0]
                if not df_season.empty:
                    team_games_list.append(df_season)
            except Exception:
                pass
            time.sleep(0.6)
        if team_games_list:
            master_team_df = pd.concat(team_games_list, ignore_index=True)
            master_team_df['GAME_DATE'] = pd.to_datetime(master_team_df['GAME_DATE'])
            master_team_df = master_team_df.sort_values('GAME_DATE').reset_index(drop=True)
            master_team_df.to_csv(filename, index=False)

def download_all_teams_advanced_master_csvs(start_year=2015, end_year=2025, output_dir="nba_advanced_master_csvs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    seasons = [f"{year}-{str(year + 1)[-2:]}" for year in range(start_year, end_year + 1)]
    all_teams = teams.get_teams()
    for idx, team in enumerate(all_teams, start=1):
        clean_name = team['full_name'].replace(" ", "_")
        filename = os.path.join(output_dir, f"advanced_{clean_name}_all_games_{start_year}_{end_year + 1}.csv")
        if os.path.exists(filename):
            continue
        team_games_list = []
        for season in seasons:
            try:
                advanced_logs = teamgamelogs.TeamGameLogs(
                    team_id_nullable=team['id'],
                    season_nullable=season,
                    measure_type_player_game_logs_nullable='Advanced'
                )
                df_season = advanced_logs.get_data_frames()[0]
                if not df_season.empty:
                    team_games_list.append(df_season)
            except Exception:
                pass
            time.sleep(0.6)
        if team_games_list:
            master_team_df = pd.concat(team_games_list, ignore_index=True)
            master_team_df['GAME_DATE'] = pd.to_datetime(master_team_df['GAME_DATE'])
            master_team_df = master_team_df.sort_values('GAME_DATE').reset_index(drop=True)
            master_team_df.to_csv(filename, index=False)

# Check and auto-generate data if missing
def ensure_data_exists():
    basic_files = glob.glob("nba_basic_master_csvs/*.csv")
    adv_files = glob.glob("nba_advanced_master_csvs/*.csv")
    if not basic_files or not adv_files:
        st.warning("⚠️ Local CSV data missing. Fetching historical data from NBA API...")
        with st.spinner("Downloading team master CSVs..."):
            download_all_teams_basic_stats_master_csvs()
            download_all_teams_advanced_master_csvs()
        st.success("✅ Data download complete!")
        st.rerun()

ensure_data_exists()

# ==========================================
# 2. HOME PAGE INTERFACE
# ==========================================
st.title("🏀 NBA Historical Analytics Hub")

st.markdown("""
Welcome to the **NBA Analytics Dashboard**! Use the navigation sidebar on the left to explore different views:

---
### 📌 Available Dashboard Pages:
1. **📊 Team Stats (`pages/Team_Stats.py`)**
   - Track team performance over 10 years (2015–Present).
   - Wins/Losses per season breakdowns.
   - Rolling averages for basic stats (Points, Rebounds, Assists) and advanced efficiency ratings (Net Rating, Pace, eFG%).

""")