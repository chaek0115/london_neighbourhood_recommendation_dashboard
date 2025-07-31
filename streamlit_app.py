import streamlit as st
import pandas as pd
import math
import sys
import os 
sys.path.append(os.path.join(os.path.dirname(__file__), "api"))
from api_commute import get_commute_times_all_modes
import time
import json
import hashlib 
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("Google API key not found.")
    
CACHE_FILE = "cache_commute_times.json"


# create cache to use API calls less 
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        commute_cache = json.load(f)
else:
    commute_cache = {}

    

# load the main dataset
@st.cache_data
def load_data():
    df = pd.read_csv("final_data/final_v3_datatype.csv")
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data()



# custom CSS for multiselect tag options only
st.markdown("""
    <style>
    div[data-baseweb="tag"] {
        background-color: #f0f0f0 !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
        font-weight: 500;
    }
    div[data-baseweb="tag"] span {
        color: #000000 !important;
    }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Make the main container full width */
    .block-container {
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 90% !important;
    }

    /* Widen the sidebar */
    section[data-testid="stSidebar"] > div {
        width: 320px;
    }

    /* Prevent text wrapping in cards */
    .element-container {
        overflow: visible !important;
    }
    </style>
""", unsafe_allow_html=True)



# sidebar filters 
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


bedroom_options = sorted(df["bedrooms"].unique())
bedroom = st.sidebar.selectbox("Number of Bedrooms", bedroom_options)

bathroom_options = sorted(df["bathrooms"].unique())
bathroom = st.sidebar.selectbox("Number of Bathrooms", bathroom_options)

livingroom_options = sorted(df["livingrooms"].unique())
livingroom = st.sidebar.selectbox("Number of living Rooms", livingroom_options)

property_types = df["propertytype_converted"].unique().tolist()
property = st.sidebar.selectbox("Property Type", property_types)

tenure_types = df["tenure"].unique().tolist()
tenure = st.sidebar.selectbox("Tenure Type", tenure_types)

school_options = ["Good", "Outstanding", "No info"]
school = st.sidebar.multiselect("School Rating", school_options, default=school_options)

crime_level_options = ["High crime", "Medium crime", "Low crime", "No info"]
crime = st.sidebar.multiselect("Crime Level", crime_level_options, default=crime_level_options)




# filter data
df_filtered = df.copy()
df_filtered = df[
    (df["median_price"].between(budget_min, budget_max)) &
    (df["bedrooms"] == bedroom) &
    (df["bathrooms"] == bathroom) &
    (df["propertytype_converted"] == property) &
    (df["tenure"] == tenure) &
    (df["crime_level"].isin(crime))
    ]

if livingroom is not None:
    df_filtered = df_filtered[df_filtered["livingrooms"] == livingroom]

# filter by school data
school_filter = (
    ((df["num_good"] > 0) & ("Good" in school)) | 
    ((df["num_outstanding"] > 0) & ("Outstanding" in school)) |
    (((df["num_good"] == 0) & (df["num_outstanding"]== 0)) & ("No info" in school))
    )

df_filtered = df_filtered[school_filter]






# Commute settings
work_address = st.sidebar.text_input("Enter your work address (optional)")
work_address = work_address.strip().lower()

def extract_minutes(duration_str):
    if pd.isna(duration_str) or not isinstance(duration_str, str):
        return None
    
    try:
        duration_str = duration_str.lower().replace("hr", "hour")
        hour_minutes = duration_str.split("hour")
        total_minutes = 0
        
        if len(hour_minutes) == 2:
            hours = int(hour_minutes[0].strip())
            minutes_part = hour_minutes[1].replace("mins", "").strip()
            minutes = int(hour_minutes[1].replace("mins","")).strip()
            total_minutes = hours * 60 + minutes
        elif "mins" in hour_minutes[0]:
            minutes = int(hour_minutes[0].replace("mins","").strip()) 
            total_minutes = minutes
        else:
            return None
        return total_minutes
    except Exception as e:
        return None





# commute time calculation
if work_address:
    with st.spinner("Calculating commute times..."):
        df_area_outcode = df[["area name", "outcode", "latitude", "longitude"]].drop_duplicates()
        commute_results = []
        
        for _, row in df_area_outcode.iterrows():
            lat = float(row["latitude"])
            lng = float(row["longitude"])
            origin = f"{lat:.4f}, {lng:.4f}"
            key = f"{origin}|{work_address.strip().lower()}"
            
            if key in commute_cache:
                durations = commute_cache[key]
            else:
                durations = get_commute_times_all_modes(origin, work_address, api_key)
                time.sleep(0.5)  # avoid hitting API rate limits
                
                if durations and any(extract_minutes(v) is not None for v in durations.values()):
                    commute_cache[key] = durations
                    with open(CACHE_FILE, "w") as f:
                        json.dump(commute_cache, f)
            
            if not durations:
                continue
            
            valid_durations = {k: v for k, v in durations.items() if extract_minutes(v) is not None}
            if not valid_durations:
                continue
            
            best_mode = min(valid_durations, key=lambda k: extract_minutes(valid_durations[k]))
            best_time = valid_durations[best_mode]
            
            commute_results.append({
                "area name": row["area name"],
                "outcode": row["outcode"],
                "best_mode": best_mode,
                "duration_text": best_time,
                "duration_mins": extract_minutes(best_time)
            })
            
        commute_df = pd.DataFrame(commute_results)
        df = df.merge(commute_df, on=["outcode","area name"], how="left")
        
   
    
# apply filters - commute
if work_address and "duration_mins" in df_filtered.columns:
    max_commute = st.sidebar.slider("Max Commute Time (mins)", 10, 120, 30)
    df_filtered = df_filtered[df_filtered["duration_mins"] <= max_commute]    
    
    
    
    
# Sort options
sort_option = st.sidebar.selectbox("Sort by", [
    "Default",
    "Price: Low to High",
    "Price: High to Low"
])

# apply sorting
if sort_option == "Price: Low to High":
    df_filtered = df_filtered.sort_values("median_price", ascending=True)
elif sort_option == "Price: High to Low":
    df_filtered = df_filtered.sort_values("median_price", ascending=False)
# "Default" will leave the current order as is
   




# show results - main screen
st.title("🏠 London Neighbourhood Recommender")
st.markdown(f"### 🔎 {len(df_filtered)} neighbourhoods match your search")

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
                # MAP VIEW
                st.markdown(
                    f"""
                    <div style='background-color:#f9f9f9; border-radius:10px; padding:10px; border:1px solid #ccc;'>
                        <div style='font-size:20px; font-weight:bold;'>🗺️ Map for {row['ward']} | {row['outcode']}</div>
                    </div>
                    """, unsafe_allow_html=True
                )

                st.map(pd.DataFrame({
                    "lat": [row["latitude"]],
                    "lon": [row["longitude"]]
                }))

                if st.button("🔙 Back to Info", key=f"back-btn-{i}"):
                    st.session_state[map_key] = False

            else:
                card_container = st.container()
                with card_container:
                    card_html = f"""
                    <div style='
                        background-color: white;
                        color: black;
                        padding: 0;
                        border-radius: 10px;
                        border: 1px solid #ccc;
                        margin: 6px 3px;
                        font-size: 16px;
                        overflow: hidden;
                    '>
                        <div style='
                            background-color: #f0f0f0;
                            padding: 10px 15px;
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            border-top-left-radius: 10px;
                            border-top-right-radius: 10px;
                        '>
                            <div style='font-weight: bold; font-size: 18px;'>📍 {row['ward']}</div>
                        </div>
                        <div style='padding: 15px;'>
                            📫 <strong>{row['outcode']} | {row['district']}</strong><br>
                            💰 <strong>Median Price:</strong> £{row['median_price']:,.0f}<br>
                            🚈 <strong>Nearest Station:</strong> {row['nearest_station']}<br>
                            🚨 <strong>Crime Rate:</strong> {row['crime_level']}<br>
                            <hr style='border: 1px solid #ddd; margin: 6px 0;'>
                    """

                    # Top 3 crimes
                    top_crimes = [row.get("crime_1"), row.get("crime_2"), row.get("crime_3")]
                    top_crimes = [crime for crime in top_crimes if pd.notna(crime) and crime.lower() != "no info"]
                    if top_crimes:
                        card_html += f"👮<strong>Top 3 Crimes:</strong> {', '.join(top_crimes)}<br>"
                    else:
                        card_html += "👮<strong>Top 3 Crimes:</strong> No info<br>"

                    # School info
                    good = row.get("num_good", 0)
                    outstanding = row.get("num_outstanding", 0)
                    school_lines = []
                    if outstanding > 0:
                        school_lines.append(f"{outstanding} outstanding school(s): {row.get('schools_outstanding', '')}")
                    if good > 0:
                        school_lines.append(f"{good} good school(s): {row.get('schools_good', '')}")
                    if school_lines:
                        for line in school_lines:
                            if ":" in line:
                                label, school_names = line.split(":", 1)
                                card_html += f"🏫 <strong>{label}:</strong>{school_names}<br>"
                    else:
                        card_html += "🏫 <strong>School:</strong> No info<br>"

                    card_html += "</div></div>"
                    st.markdown(card_html, unsafe_allow_html=True)

                    # Handle form trigger manually
                    view_map_clicked = st.button("🗺️ View on Map", key=f"view_map_btn_{i}")
                    if view_map_clicked:
                        st.session_state[map_key] = True


