import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from pybaseball import standings, schedule_and_record, batting_stats_bref, pitching_stats_bref, cache

# 1. SETUP & CACHING
cache.enable()
st.set_page_config(page_title="MLB Pro Dashboard", layout="wide", page_icon="⚾")

# This header makes the cloud server look like a real person browsing
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# 2. HELPER FUNCTIONS WITH CACHING
@st.cache_data(ttl=86400) # Save data for 24 hours
def get_standings_safe(year):
    # We use requests first to 'warm up' the connection if needed
    return standings(year)

def check_bref_status():
    try:
        # Test connection with headers
        response = requests.get("https://www.baseball-reference.com/robots.txt", headers=HEADERS, timeout=5)
        if response.status_code == 200: return "Online", "🟢"
        if response.status_code == 429: return "Rate Limited", "🟡"
        return f"Blocked ({response.status_code})", "🔴"
    except:
        return "Offline", "⚪"

# 3. SIDEBAR
curr_year = datetime.now().year
with st.sidebar:
    st.title("⚙️ System Tools")
    status, icon = check_bref_status()
    st.metric("BRef Server Status", status, delta=icon)
    if st.button("Clear App Cache"):
        cache.purge()
        st.cache_data.clear()
        st.success("Cache cleared!")

# 4. MAIN APP
st.title("⚾ MLB Data Dashboard (1900-2025)")
tab1, tab2, tab3, tab4 = st.tabs(["Standings", "Team Results", "Hitters", "Pitchers"])

# --- TAB 1: STANDINGS (AUTOMATIC) ---
with tab1:
    st.header("Division Standings")
    year_list = list(range(curr_year, 1899, -1))
    yr_choice = st.selectbox("Select Season", options=year_list, index=1, key="st_auto") # Default to 2024

    try:
        with st.spinner(f"Fetching {yr_choice} data..."):
            data = get_standings_safe(yr_choice)
            if data:
                for df in data:
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning(f"No standings available for {yr_choice}. BRef may be blocking the request.")
    except Exception as e:
        st.error("Connection blocked by Baseball-Reference. Please try clearing cache or wait 60 seconds.")

# --- TAB 2: TEAM RESULTS (AUTOMATIC) ---
with tab2:
    st.header("Team Schedule")
    teams = ["NYY", "LAD", "ATL", "BOS", "CHC", "PHI", "HOU", "NYM", "TOR", "TEX"] # Short list for example
    c1, c2 = st.columns(2)
    with c1:
        t_choice = st.selectbox("Team", options=teams, key="t_auto")
    with c2:
        y_choice = st.selectbox("Year", options=year_list, index=1, key="ty_auto")
    
    try:
        if y_choice == 2025:
            st.info("2025 Schedule not yet available.")
        else:
            res = schedule_and_record(y_choice, t_choice)
            st.dataframe(res, use_container_width=True)
    except:
        st.error("Could not retrieve schedule.")
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