import streamlit as st
import pandas as pd
import math
import sys
import os 
import time
import json
import hashlib 

# load the main dataset
@st.cache_data
def load_data():
    df = pd.read_csv("final_data/final_v3_datatype.csv")
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data() 



# custom CSS 
st.markdown("""
    <style>
    /* Sidebar wrapper */
    section[data-testid="stSidebar"] {
        border-right: none !important;
        box-shadow: none !important;
        padding: 1rem 0.5rem !important;
        width: 320px !important;
    }

    section[data-testid="stSidebar"] > div {
        width: 280px;
        margin: auto;
    }

    .block-container {
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 90% !important;
    }

    .element-container {
        overflow: visible !important;
    }

    /* 🌞 Light mode */
    @media (prefers-color-scheme: light) {
        section[data-testid="stSidebar"] {
            background-color: #f5f5f5 !important;  /* light grey */
            color: #000000 !important;             /* black text */
        }

        [data-baseweb="tag"] {
            background-color: #d4edda !important;  /* sage green */
            border: 1px solid #b2d8c2 !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }

        [data-baseweb="tag"] span,
        [data-baseweb="tag"] svg path {
            color: #000000 !important;
            fill: #000000 !important;
        }
    }

    /* 🌙 Dark mode */
    @media (prefers-color-scheme: dark) {
        section[data-testid="stSidebar"] {
            background-color: #374151 !important;   /* Tailwind Grey 700 */
            color: #ffffff !important;              /* white text */
        }

        [data-baseweb="tag"] {
            background-color: #4d5c34 !important;   /* dark olive green */
            border: 1px solid #3d4a2c !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }

        [data-baseweb="tag"] span,
        [data-baseweb="tag"] svg path {
            color: #ffffff !important;
            fill: #ffffff !important;
        }
    }

    /* Remove number spinner buttons */
    input[type=number]::-webkit-inner-spin-button,
    input[type=number]::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
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
                        <div style='font-size:25px; font-weight:bold; color:black;'>🗺️ {row['ward']} | {row['outcode']}</div>
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
                        font-size: 20px;
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
                            <div style='font-weight: bold; font-size: 25px;'>📍 {row['ward']}</div>
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


