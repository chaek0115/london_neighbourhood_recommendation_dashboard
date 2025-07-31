import streamlit as st
import pandas as pd
import math
import sys
import os
import time
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "api"))
from api_commute import get_commute_times_all_modes

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("Google API key not found.")

CACHE_FILE = "cache_commute_times.json"
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        commute_cache = json.load(f)
else:
    commute_cache = {}

@st.cache_data
def load_data():
    df = pd.read_csv("final_data/final_v3_datatype.csv")
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data()

# ---- UI CSS ----
st.markdown("""
    <style>
    .block-container { padding-left: 3rem !important; padding-right: 3rem !important; max-width: 90% !important; }
    section[data-testid="stSidebar"] > div { width: 320px; }
    div[data-baseweb="tag"] { background-color: #f0f0f0 !important; color: #000 !important; border-radius: 8px !important; font-weight: 500; }
    div[data-baseweb="tag"] span { color: #000 !important; }
    </style>
""", unsafe_allow_html=True)


# ---- Sidebar Filters ----
st.sidebar.header("⚙️ Filter Options")
st.sidebar.markdown("**Budget (£)**")
min_price = int(df["median_price"].min())
max_price = int(df["median_price"].max())
budget_min = st.sidebar.number_input(
    "Minimum Budget", min_value=0, max_value=max_price, value=0, step=100000
)
st.sidebar.caption(f"Selected Min Budget: £{budget_min:,}")
budget_max = st.sidebar.number_input(
    "Maximum Budget", min_value=0, max_value=max_price, value=0, step=100000
)
st.sidebar.caption(f"Selected Max Budget: £{budget_max:,}")

if budget_min > budget_max:
    st.sidebar.error("Minimum budget cannot be greater than maximum budget.")
    
    
bedroom = st.sidebar.selectbox("Bedrooms", sorted(df["bedrooms"].unique()))
bathroom = st.sidebar.selectbox("Bathrooms", sorted(df["bathrooms"].unique()))
livingroom = st.sidebar.selectbox("Living Rooms", sorted(df["livingrooms"].unique()))
property = st.sidebar.selectbox("Property Type", df["propertytype_converted"].unique())
tenure = st.sidebar.selectbox("Tenure Type", df["tenure"].unique())
school = st.sidebar.multiselect("School Rating", ["Good", "Outstanding", "No info"], default=["Good", "Outstanding", "No info"])
crime = st.sidebar.multiselect("Crime Level", ["High crime", "Medium crime", "Low crime", "No info"], default=["High crime", "Medium crime", "Low crime", "No info"])


# ---- Filtering ----
df_filtered = df[
    (df["median_price"].between(budget_min, budget_max)) &
    (df["bedrooms"] == bedroom) &
    (df["bathrooms"] == bathroom) &
    (df["livingrooms"] == livingroom) &
    (df["propertytype_converted"] == property) &
    (df["tenure"] == tenure) &
    (df["crime_level"].isin(crime))
]
school_filter = (
    ((df["num_good"] > 0) & ("Good" in school)) |
    ((df["num_outstanding"] > 0) & ("Outstanding" in school)) |
    (((df["num_good"] == 0) & (df["num_outstanding"] == 0)) & ("No info" in school))
)
df_filtered = df_filtered[school_filter]


# ---- Commute Filtering ----
work_address = st.sidebar.text_input("Enter your work address (optional)").strip().lower()
def extract_minutes(s):
    try:
        s = s.lower().replace("hr", "hour")
        if "hour" in s:
            h, m = s.split("hour")
            return int(h.strip()) * 60 + int(m.replace("mins", "").strip())
        return int(s.replace("mins", "").strip())
    except: return None

if work_address:
    with st.spinner("Calculating commute times..."):
        commute_data = []
        for _, row in df[["area name", "outcode", "latitude", "longitude"]].drop_duplicates().iterrows():
            lat, lng = row["latitude"], row["longitude"]
            origin = f"{lat:.4f}, {lng:.4f}"
            key = f"{origin}|{work_address}"
            durations = commute_cache.get(key)
            if not durations:
                durations = get_commute_times_all_modes(origin, work_address, api_key)
                if durations: commute_cache[key] = durations
                time.sleep(0.5)
            valid = {k: v for k, v in durations.items() if extract_minutes(v) is not None} if durations else {}
            if valid:
                best = min(valid, key=lambda k: extract_minutes(valid[k]))
                commute_data.append({"area name": row["area name"], "outcode": row["outcode"], "best_mode": best, "duration_text": valid[best], "duration_mins": extract_minutes(valid[best])})
        df = df.merge(pd.DataFrame(commute_data), on=["area name", "outcode"], how="left")
        with open(CACHE_FILE, "w") as f: json.dump(commute_cache, f)

    max_commute = st.sidebar.slider("Max Commute Time (mins)", 10, 120, 30)
    df_filtered = df_filtered[df_filtered["duration_mins"] <= max_commute]


# ---- Sorting ----
sort_option = st.sidebar.selectbox("Sort by", ["Default", "Price: Low to High", "Price: High to Low"])
if sort_option == "Price: Low to High":
    df_filtered = df_filtered.sort_values("median_price")
elif sort_option == "Price: High to Low":
    df_filtered = df_filtered.sort_values("median_price", ascending=False)


# ---- Main Results ----
st.title("\U0001F3E0 London Neighbourhood Recommender")
st.markdown(f"### \U0001F50D {len(df_filtered)} neighbourhoods match your search")

if df_filtered.empty:
    st.warning("No results found. Please adjust your filters.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(df_filtered.iterrows()):
        j = i % 3
        map_key = f"show_map_{i}"
        if map_key not in st.session_state:
            st.session_state[map_key] = False

        with cols[j]:
            if st.session_state[map_key]:
                st.markdown(f"### 🗺️ Map for {row['ward']} | {row['outcode']}")
                st.map(pd.DataFrame({"lat": [row["latitude"]], "lon": [row["longitude"]]}))
                if st.button("🔙 Back", key=f"back-btn-{i}"):
                    st.session_state[map_key] = False
            else:
                card = st.container()
                with card:
                    top = st.columns([4, 1])
                    with top[0]:
                        st.markdown(f"### 📍 {row['ward']}")
                    with top[1]:
                        if st.button("🗺️ View on Map", key=f"view_map_btn_{i}"):
                            st.session_state[map_key] = True

                    html = f"""
                    <div style='background-color:white; color:black; padding:15px; border-radius:10px; border:1px solid #ccc;'>
                        📫 <strong>{row['outcode']} | {row['district']}</strong><br>
                        💰 <strong>Median Price:</strong> £{row['median_price']:,.0f}<br>
                        🚈 <strong>Nearest Station:</strong> {row['nearest_station']}<br>
                        🚨 <strong>Crime Rate:</strong> {row['crime_level']}<br>
                        <hr>
                    """
                    top_crimes = [row.get("crime_1"), row.get("crime_2"), row.get("crime_3")]
                    top_crimes = [c for c in top_crimes if pd.notna(c) and c.lower() != "no info"]
                    html += f"👮 <strong>Top 3 Crimes:</strong> {', '.join(top_crimes)}<br>" if top_crimes else "👮 <strong>Top 3 Crimes:</strong> No info<br>"
                    good, outstanding = row.get("num_good", 0), row.get("num_outstanding", 0)
                    if outstanding:
                        html += f"🏫 <strong>{outstanding} outstanding school(s):</strong> {row.get('schools_outstanding', 'No info')}<br>"
                    if good:
                        html += f"🏫 <strong>{good} good school(s):</strong> {row.get('schools_good', 'No info')}<br>"
                    if good == 0 and outstanding == 0:
                        html += "🏫 <strong>School:</strong> No info<br>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                    
                    