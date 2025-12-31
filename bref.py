import streamlit as st
import pandas as pd
import unicodedata
import requests
from pybaseball import standings, schedule_and_record, batting_stats_bref, pitching_stats_bref, cache

from datetime import datetime

# Get the current year dynamically
curr_year = datetime.now().year

# 1. SETUP & CACHING
try:
    cache.enable()
except:
    pass

st.set_page_config(page_title="MLB Pro Dashboard", layout="wide", page_icon="⚾")

# 2. HELPER FUNCTIONS
def strip_accents(text):
    """Normalize names like 'José' to 'Jose' for easier searching."""
    if not isinstance(text, str): return text
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

def check_bref_status():
    """Checks if Baseball-Reference is reachable or blocking the script."""
    try:
        response = requests.get("https://www.baseball-reference.com/robots.txt", timeout=5)
        if response.status_code == 200: return "Online", "🟢"
        if response.status_code == 429: return "Rate Limited", "🟡"
        return "Blocked", "🔴"
    except:
        return "Offline", "⚪"

@st.cache_data(show_spinner=False)
def get_cached_standings(year):
    return standings(year)

@st.cache_data(show_spinner=False)
def get_cached_batting(year):
    return batting_stats_bref(year)

# 3. SIDEBAR TOOLS
with st.sidebar:
    st.title("⚙️ System Tools")
    status, icon = check_bref_status()
    st.metric("BRef Server Status", status, delta=icon, delta_color="normal")
    
    if st.button("Clear App Cache"):
        cache.purge()
        st.success("Cache cleared!")
    
    st.divider()
    st.info("Tip: If tabs return 'Nothing', BRef might be rate-limiting you. Wait 30s.")

# 4. MAIN APP UI
st.title("⚾ MLB Data Dashboard (1900-2025)")

tab1, tab2, tab3, tab4 = st.tabs([
    "Division Standings", 
    "Team Results", 
    "Hitter Search", 
    "Pitcher Search"
])

# --- TAB 1: STANDINGS ---
with tab1:
    st.header("Division Standings")
    
    # 1. Setup the year list
    year_list = list(range(curr_year, 1899, -1))
    
    # 2. Selectbox - The app will automatically rerun when this changes
    yr_choice = st.selectbox("Select Season", options=year_list, index=0, key="st_yr_auto")

    # 3. Automatic Loading logic
    try:
        # We still use a spinner so the user knows it's working
        with st.spinner(f"Loading {yr_choice} Standings..."):
            data = get_cached_standings(yr_choice)
            
            if data:
                # Use columns to make it look organized if multiple tables return
                for df in data:
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning(f"No standings data available for {yr_choice}.")
                
    except Exception as e:
        st.error(f"Error loading standings: {e}")

# --- TAB 2: TEAM RESULTS ---
with tab2:
    st.header("Team Schedule & Record")
    modern_teams = ["ARI", "ATL", "BAL", "BOS", "CHC", "CHW", "CIN", "CLE", "COL", "DET",
                    "HOU", "KCR", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY", "OAK",
                    "PHI", "PIT", "SDP", "SEA", "SFG", "STL", "TBR", "TEX", "TOR", "WSN"]
    
    c1, c2 = st.columns(2)
    with c1:
        team_choice = st.selectbox("Team Abbr", options=modern_teams, index=18, accept_new_options=True)
    with c2:
        # 1. Create the list of years
        year_list = list(range(curr_year, 1899, -1))

        # 2. Capture the SINGLE year selected by the user
        yr_choice = st.selectbox("Select Season", options=year_list, index=0, key="st_yr_select")

    if st.button("Fetch Schedule"):
        try:
            with st.spinner("Downloading..."):
                res = schedule_and_record(yr_choice, team_choice.upper())
                if res is not None:
                    st.dataframe(res, use_container_width=True)
                else:
                    st.error("Table not found. Team may not have existed then.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 3: HITTER SEARCH ---
with tab3:
    st.header("Hitter Statistics")
    c3, c4 = st.columns([1, 2])
    with c3:
        yr_3 = st.number_input("Year", 1900, 2025, 2024, key="hit_yr")
    with c4:
        h_query = st.text_input("Player Name Search", placeholder="e.g. Ohtani")

    if st.button("Search Hitters"):
        try:
            with st.spinner("Loading Hitters..."):
                df = batting_stats_bref(yr_3)
                df['CleanName'] = df['Name'].apply(strip_accents)
                results = df[df['CleanName'].str.contains(h_query, case=False)]
                
                cols = ['Name', 'Tm', 'G', 'AB', 'R', 'H', 'HR', 'RBI', 'BA', 'OBP', 'SLG', 'OPS']
                available = [c for c in cols if c in results.columns]
                st.dataframe(results[available], use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 4: PITCHER SEARCH ---
with tab4:
    st.header("Pitcher Statistics")
    c5, c6 = st.columns([1, 2])
    with c5:
        yr_4 = st.number_input("Year", 1900, 2025, 2024, key="pitch_yr")
    with c6:
        p_query = st.text_input("Pitcher Name Search", placeholder="e.g. Skenes")

    if st.button("Search Pitchers"):
        try:
            with st.spinner("Loading Pitchers..."):
                pdf = pitching_stats_bref(yr_4)
                
                # League Average Stats
                m1, m2, m3 = st.columns(3)
                m1.metric("League Avg ERA", round(pdf['ERA'].mean(), 2))
                m2.metric("League Avg WHIP", round(pdf['WHIP'].mean(), 2))
                m3.metric("League Avg SO", int(pdf['SO'].mean()))
                st.divider()

                pdf['CleanName'] = pdf['Name'].apply(strip_accents)
                p_results = pdf[pdf['CleanName'].str.contains(p_query, case=False)]
                
                p_cols = ['Name', 'Tm', 'G', 'W', 'L', 'BB', 'SO', 'ERA', 'WHIP', 'ERA+', 'SV']
                p_avail = [c for c in p_cols if c in p_results.columns]
                st.dataframe(p_results[p_avail], use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")