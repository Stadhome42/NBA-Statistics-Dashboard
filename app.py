import time
import pandas as pd
import os
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import leaguegamefinder, playergamelog, leaguegamelog, teamgamelogs
from dashboard import run_dashboard
import streamlit as st


def get_all_nba_teams():
    # Retrieve all NBA teams
    all_teams = teams.get_teams()
    return all_teams

# def test_nba_team_games():
#     print("--- 1. Testing NBA Team Game Finder ---")
    
#     # Query regular season games for the 2024-2025 season
#     # (League ID '00' corresponds to the NBA)
#     game_finder = leaguegamefinder.LeagueGameFinder(
#         season_nullable='2024-25',
#         league_id_nullable='00'
#     )
    
#     # Retrieve data directly as a Pandas DataFrame
#     games_df = game_finder.get_data_frames()[0]
    
#     print(f"Successfully retrieved {len(games_df)} game records!")
#     print("\nSample Data (First 5 Games):")
#     print(games_df[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'PLUS_MINUS']].head())
#     print("\n" + "="*50 + "\n")

# def test_nba_player_stats(player_name="LeBron James"):
#     print(f"--- 2. Testing Player Lookup & Game Logs ({player_name}) ---")
    
#     # Search for player by name
#     found_players = players.find_players_by_full_name(player_name)
#     if not found_players:
#         print(f"Player '{player_name}' not found.")
#         return
    
#     player_info = found_players[0]
#     player_id = player_info['id']
#     print(f"Found Player: {player_info['full_name']} (ID: {player_id})")
    
#     # Polite pause before the next request to prevent IP rate throttling
#     time.sleep(1)
    
#     # Query game logs for the specified player
#     gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='2024-25')
#     df_gamelog = gamelog.get_data_frames()[0]
    
#     print(f"Successfully retrieved {len(df_gamelog)} game log rows!")
#     print("\nSample Player Box Scores (First 5 Games):")
#     print(df_gamelog[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'STL', 'BLK']].head())

def download_all_teams_basic_stats_master_csvs(start_year=2015, end_year=2025, output_dir="nba_basic_master_csvs"):
    """
    Downloads traditional/basic game logs (PTS, REB, AST, FGM, etc.) team-by-team 
    across multiple seasons, and consolidates each team's full history into 1 master CSV.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: '{output_dir}/'")

    # Build list of season strings ('2015-16', '2016-17', ..., '2024-25')
    seasons = [f"{year}-{str(year + 1)[-2:]}" for year in range(start_year, end_year + 1)]
    
    all_teams = teams.get_teams()
    print(f"Starting basic stats data extraction for {len(all_teams)} teams across {len(seasons)} seasons...\n")

    for idx, team in enumerate(all_teams, start=1):
        team_id = team['id']
        team_name = team['full_name']
        team_games_list = []

        clean_name = team_name.replace(" ", "_")
        
        # Naming convention for basic stats CSVs
        filename = os.path.join(output_dir, f"basic_{clean_name}_{start_year}_{end_year + 1}.csv")
        
        # Skip if the file already exists
        if os.path.exists(filename):
            print(f"[{idx}/32] Skipping {team_name} — file already exists: '{filename}'")
            continue
        
        print(f"[{idx}/32] Processing {team_name}...")

        for season in seasons:
            try:
                # Use 'Base' instead of 'Advanced' to fetch traditional box scores
                basic_logs = teamgamelogs.TeamGameLogs(
                    team_id_nullable=team_id,
                    season_nullable=season,
                    measure_type_player_game_logs_nullable='Base'
                )
                
                df_season = basic_logs.get_data_frames()[0]
                
                if not df_season.empty:
                    team_games_list.append(df_season)
                    
            except Exception as e:
                print(f"  -> Error for {team_name} in {season}: {e}")

            # Polite pause to respect NBA.com rate limits
            time.sleep(1)

        # Combine all years for this specific team into one DataFrame
        if team_games_list:
            master_team_df = pd.concat(team_games_list, ignore_index=True)
            master_team_df['GAME_DATE'] = pd.to_datetime(master_team_df['GAME_DATE'])
            master_team_df = master_team_df.sort_values('GAME_DATE').reset_index(drop=True)
                    
            master_team_df.to_csv(filename, index=False)
            print(f"  -> Saved {len(master_team_df)} basic games to '{filename}'\n")
        else:
            print(f"  -> No data found for {team_name}\n")

def download_all_teams_advanced_master_csvs(start_year=2015, end_year=2025, output_dir="nba_advanced_master_csvs"):
    """
    Downloads advanced game logs (Net Rating, Pace, eFG%, etc.) team-by-team 
    across multiple seasons, and consolidates each team's full history into 1 master CSV.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: '{output_dir}/'")

    seasons = [f"{year}-{str(year + 1)[-2:]}" for year in range(start_year, end_year + 1)]
    
    all_teams = teams.get_teams()
    print(f"Starting advanced data extraction for {len(all_teams)} teams across {len(seasons)} seasons...\n")

    for idx, team in enumerate(all_teams, start=1):
        team_id = team['id']
        team_name = team['full_name']
        team_games_list = []

        clean_name = team_name.replace(" ", "_")
        filename = os.path.join(output_dir, f"advanced_{clean_name}_all_games_{start_year}_{end_year + 1}.csv")
        
        # 2. Skip if the file already exists
        if os.path.exists(filename):
            print(f"[{idx}/32] Skipping {team_name} — file already exists: '{filename}'")
            continue
        
        print(f"[{idx}/32] Processing {team_name}...")

        for season in seasons:
            try:
                # TeamGameLogs successfully accepts the Advanced parameter
                advanced_logs = teamgamelogs.TeamGameLogs(
                    team_id_nullable=team_id,
                    season_nullable=season,
                    measure_type_player_game_logs_nullable='Advanced'
                )
                
                df_season = advanced_logs.get_data_frames()[0]
                
                if not df_season.empty:
                    team_games_list.append(df_season)
                    
            except Exception as e:
                print(f"  -> Error for {team_name} in {season}: {e}")

            time.sleep(1)

        # Combine all years for this specific team into one DataFrame
        if team_games_list:
            master_team_df = pd.concat(team_games_list, ignore_index=True)
            master_team_df['GAME_DATE'] = pd.to_datetime(master_team_df['GAME_DATE'])
            master_team_df = master_team_df.sort_values('GAME_DATE').reset_index(drop=True)
                        
            master_team_df.to_csv(filename, index=False)
            print(f"  -> Saved {len(master_team_df)} games to '{filename}'\n")
        else:
            print(f"  -> No data found for {team_name}\n")

if __name__ == "__main__":
    try:
        # test_nba_team_games()
        # test_nba_player_stats("LeBron James")
        download_all_teams_basic_stats_master_csvs()
        download_all_teams_advanced_master_csvs()
        run_dashboard()

    except Exception as e:
        print(f"\nAn error occurred while connecting to nba_api: {e}")