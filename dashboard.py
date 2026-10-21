import os
import glob
import pandas as pd
import plotly.express as px
import streamlit as st

def run_dashboard():
    st.set_page_config(page_title="NBA Advanced Analytics Dashboard", layout="wide")

    st.title("🏀 NBA Team Advanced & Basic Analytics Dashboard")

    ADVANCE_DATA_DIR = "nba_advanced_master_csvs"
    BASIC_DATA_DIR = "nba_basic_master_csvs"

    # Locate advanced CSVs in the output directory
    csv_files = glob.glob(os.path.join(ADVANCE_DATA_DIR, "*.csv"))

    if not csv_files:
        st.error(f"No CSV files found in directory '{ADVANCE_DATA_DIR}/'. Please run your data extraction script first.")
        st.stop()

    # Parse clean team names from advanced file names
    file_map = {}
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        clean_name = filename.replace("advanced_", "").rsplit("_all_games", 1)[0].replace("_", " ")
        file_map[clean_name] = filepath

    # Sidebar Navigation
    st.sidebar.header("Dashboard Controls")
    selected_team = st.sidebar.selectbox("Select Team", sorted(list(file_map.keys())))

    # --- Load Data Sources ---
    # 1. Load Advanced Team Data
    df_advanced = pd.read_csv(file_map[selected_team])
    df_advanced['GAME_DATE'] = pd.to_datetime(df_advanced['GAME_DATE'])

    # 2. Try loading Basic Team Data dynamically
    clean_team_name = selected_team.replace(" ", "_")
    basic_filepath = os.path.join(BASIC_DATA_DIR, f"basic_{clean_team_name}_2015_2026.csv")

    if os.path.exists(basic_filepath):
        df_basic = pd.read_csv(basic_filepath)
        df_basic['GAME_DATE'] = pd.to_datetime(df_basic['GAME_DATE'])
        cols_to_use = df_basic.columns.difference(df_advanced.columns).tolist()
        if 'GAME_ID' not in cols_to_use:
            cols_to_use.append('GAME_ID')
        df = pd.merge(df_advanced, df_basic[cols_to_use], on='GAME_ID', how='left')
    else:
        df = df_advanced

    # Create Season Year column (e.g., '2015-16', '2016-17') based on 6-month offset
    df['Season Start Year'] = (df['GAME_DATE'] - pd.DateOffset(months=6)).dt.year
    df['Season Year'] = df['Season Start Year'].apply(lambda x: f"{x}-{str(x + 1)[-2:]}")

    # --- Season Filter in Sidebar ---
    # Get a sorted list of unique seasons available for this specific team
    available_seasons = sorted(df['Season Year'].unique())
    season_options = ["All Years"] + available_seasons

    selected_season = st.sidebar.selectbox("Select Season", season_options)

    # Filter DataFrame based on selection
    if selected_season != "All Years":
        df_filtered = df[df['Season Year'] == selected_season].copy()
    else:
        df_filtered = df.copy()

    # Extract dynamic date strings for headers based on filtered data
    min_date_str = df_filtered['GAME_DATE'].min().strftime('%B %Y') if not df_filtered.empty else ""
    max_date_str = df_filtered['GAME_DATE'].max().strftime('%B %Y') if not df_filtered.empty else ""
    date_range_label = f"{min_date_str} to {max_date_str}" if not df_filtered.empty else "No Data"
    years_label = selected_season if selected_season != "All Years" else f"{df['GAME_DATE'].min().year}–{df['GAME_DATE'].max().year}"

    # --- Section 1: Wins & Losses Breakdown ---
    st.header(f"{selected_team} Overview ({selected_season})")
    st.subheader(f"{selected_team} — Wins & Losses Breakdown")

    if df_filtered.empty:
        st.warning("No data available for the selected season.")
        st.stop()

    wl_counts = df_filtered.groupby(['Season Year', 'WL']).size().reset_index(name='Count')

    total_wins = len(df_filtered[df_filtered['WL'] == 'W'])
    total_losses = len(df_filtered[df_filtered['WL'] == 'L'])
    win_percentage = (total_wins / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0

    w_col1, w_col2, w_col3 = st.columns(3)
    w_col1.metric("Total Wins", total_wins)
    w_col2.metric("Total Losses", total_losses)
    w_col3.metric("Win Percentage", f"{win_percentage:.1f}%")

    color_map = {'W': '#00b050', 'L': '#ff4d4d'}

    fig_wl = px.bar(
        wl_counts,
        x='Season Year',
        y='Count',
        color='WL',
        title=f"{selected_team}: Wins vs. Losses Breakdown ({selected_season})",
        labels={'Count': 'Number of Games', 'Season Year': 'Season'},
        color_discrete_map=color_map,
        barmode='group',
        template="plotly_dark"
    )
    st.plotly_chart(fig_wl, use_container_width=True)

    # --- Section 2: Basic Statistics Analysis ---
    st.markdown("---")
    st.subheader("📊 Basic Statistics Analysis")

    available_basic_metrics = [c for c in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'PLUS_MINUS'] if c in df_filtered.columns]
    metric_basic_labels = {
        'PTS': 'Points Scored',
        'REB': 'Total Rebounds',
        'AST': 'Assists',
        'STL': 'Steals',
        'BLK': 'Blocks',
        'TOV': 'Turnovers',
        'FG_PCT': 'Field Goal Percentage',
        'PLUS_MINUS': 'Plus / Minus'
    }

    if available_basic_metrics:
        selected_basic_metric = st.sidebar.selectbox(
            "Select Basic Statistic",
            available_basic_metrics,
            format_func=lambda x: metric_basic_labels.get(x, x)
        )

        basic_rolling_window = st.sidebar.slider("Basic Rolling Window (Games)", min_value=1, max_value=20, value=5, key="basic_slider")

        # Calculate Rolling Metric per season (isolated per season segment)
        df_filtered['BASIC_ROLLING'] = df_filtered.groupby('Season Year')[selected_basic_metric].transform(
            lambda x: x.rolling(window=basic_rolling_window, min_periods=1).mean()
        )

        st.subheader(f"{metric_basic_labels.get(selected_basic_metric, selected_basic_metric)} ({date_range_label})")
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        b_col1.metric(f"Average ({years_label})", f"{df_filtered[selected_basic_metric].mean():.2f}")
        b_col2.metric("Peak Value", f"{df_filtered[selected_basic_metric].max():.2f}")
        b_col3.metric("Lowest Value", f"{df_filtered[selected_basic_metric].min():.2f}")
        b_col4.metric("Total Games Analyzed", len(df_filtered))

        fig_basic = px.line(
            df_filtered,
            x='GAME_DATE',
            y='BASIC_ROLLING',
            color='Season Year',
            title=f"{selected_team}: {basic_rolling_window}-Game Rolling {metric_basic_labels.get(selected_basic_metric, selected_basic_metric)} ({selected_season})",
            labels={
                'GAME_DATE': 'Game Date',
                'BASIC_ROLLING': f'{metric_basic_labels.get(selected_basic_metric, selected_basic_metric)} ({basic_rolling_window}-Game Moving Avg)',
                'Season Year': 'Season'
            },
            hover_data=['MATCHUP', 'WL', selected_basic_metric],
            template="plotly_dark"
        )
        fig_basic.update_layout(legend_title_text='Season')
        st.plotly_chart(fig_basic, use_container_width=True)
    else:
        st.info("Basic stats CSV files not found.")

    # --- Section 3: Advanced Statistics Analysis ---
    st.markdown("---")
    st.subheader("📈 Advanced Efficiency Analysis")

    available_advanced_metrics = [c for c in ['NET_RATING', 'OFF_RATING', 'DEF_RATING', 'PACE', 'EFG_PCT', 'TS_PCT', 'PIE'] if c in df_filtered.columns]
    metric_advanced_labels = {
        'NET_RATING': 'Net Rating',
        'OFF_RATING': 'Offensive Rating',
        'DEF_RATING': 'Defensive Rating',
        'PACE': 'Pace (Possessions)',
        'EFG_PCT': 'Effective Field Goal %',
        'TS_PCT': 'True Shooting %',
        'PIE': 'Team Impact Estimate (PIE)'
    }

    if available_advanced_metrics:
        selected_advanced_metric = st.sidebar.selectbox(
            "Select Advanced Statistic", 
            available_advanced_metrics, 
            format_func=lambda x: metric_advanced_labels.get(x, x)
        )

        adv_rolling_window = st.sidebar.slider("Advanced Rolling Window (Games)", min_value=1, max_value=20, value=5, key="adv_slider")

        # Calculate Rolling Metric per season
        df_filtered['ADV_ROLLING'] = df_filtered.groupby('Season Year')[selected_advanced_metric].transform(
            lambda x: x.rolling(window=adv_rolling_window, min_periods=1).mean()
        )

        st.subheader(f"{metric_advanced_labels.get(selected_advanced_metric, selected_advanced_metric)} ({date_range_label})")
        a_col1, a_col2, a_col3, a_col4 = st.columns(4)
        a_col1.metric(f"Average ({years_label})", f"{df_filtered[selected_advanced_metric].mean():.2f}")
        a_col2.metric("Peak Value", f"{df_filtered[selected_advanced_metric].max():.2f}")
        a_col3.metric("Lowest Value", f"{df_filtered[selected_advanced_metric].min():.2f}")
        a_col4.metric("Total Games Analyzed", len(df_filtered))

        fig_adv = px.line(
            df_filtered,
            x='GAME_DATE',
            y='ADV_ROLLING',
            color='Season Year',
            title=f"{selected_team}: {adv_rolling_window}-Game Rolling {metric_advanced_labels.get(selected_advanced_metric, selected_advanced_metric)} ({selected_season})",
            labels={
                'GAME_DATE': 'Game Date',
                'ADV_ROLLING': f'{metric_advanced_labels.get(selected_advanced_metric, selected_advanced_metric)} ({adv_rolling_window}-Game Moving Avg)',
                'Season Year': 'Season'
            },
            hover_data=['MATCHUP', 'WL', selected_advanced_metric],
            template="plotly_dark"
        )
        fig_adv.update_layout(legend_title_text='Season')
        st.plotly_chart(fig_adv, use_container_width=True)

    # --- Section 4: Expandable Raw Data View ---
    with st.expander("View Raw Game Logs & Merged Data"):
        st.dataframe(df_filtered.sort_values('GAME_DATE', ascending=False), use_container_width=True)