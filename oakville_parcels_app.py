import streamlit as st
import requests
import pandas as pd
import json

# API base URL
BASE_URL = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0/query"

st.set_page_config(page_title="Oakville Parcel Viewer", layout="wide")

st.title("🏡 Oakville Parcel Data Viewer")
st.write("Fetch property parcel details (lot area, frontage, depth, address, etc.) from Oakville GIS API")

# --- User Input ---
address_input = st.text_input("Enter Property Address (optional):", "")

# Query Parameters
params = {
    "f": "json",
    "where": "1=1",
    "outFields": "*",
    "resultRecordCount": 100,   # limit results for demo
    "resultOffset": 0,
    "orderByFields": "OBJECTID ASC"
}

# If address provided, update WHERE clause
if address_input.strip():
    params["where"] = f"ADDRESS LIKE '%{address_input.strip()}%'"

# --- Fetch Data ---
if st.button("Fetch Parcel Data"):
    with st.spinner("Fetching data..."):
        try:
            response = requests.get(BASE_URL, params=params)
            data = response.json()

            if "features" not in data or len(data["features"]) == 0:
                st.warning("No results found for the given address.")
            else:
                # Convert to DataFrame
                records = [f["attributes"] for f in data["features"]]
                df = pd.DataFrame(records)

                st.success(f"✅ Found {len(df)} parcels")
                st.dataframe(df)

                # Show sample map if geometry is available
                if "geometry" in data["features"][0]:
                    st.map(pd.DataFrame([{
                        "lat": data["features"][0]["geometry"]["y"],
                        "lon": data["features"][0]["geometry"]["x"]
                    }]))
        except Exception as e:
            st.error(f"Error: {e}")
