import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import LineString

#filter the database
def filter(df, all_filters):
    
    selected_values = {}

    #display filters
    for filter in all_filters:
        selected_values[filter] = st.sidebar.selectbox(f"{filter.replace('_',' ').title()}:", options=['Select all'] + st.session_state.df_initial[filter].unique().tolist())
    
    
    filter_conditions = []

    #create list with conditions
    for filter in all_filters:
        if 'Select all' not in str(selected_values[filter]):
            filter_conditions.append(df[filter].isin([selected_values[filter]]))

    #apply conditions
    if filter_conditions:
        df_filtered = st.session_state.df_initial[pd.concat(filter_conditions, axis=1).all(axis=1)]
    else:
        df_filtered = df

    return df_filtered
    
def display_map(df):

    min_lat, max_lat, min_long, max_long = float('inf'), float('-inf'), float('inf'), float('-inf')
        
    for index, row in df.iterrows():
        # read files from run summary
        df_ex = pd.read_csv(f'{row.area_name}/{row.file_name}')
                
        # Update min and max values
        min_lat = min(min_lat, df_ex['latitude'].min())
        max_lat = max(max_lat, df_ex['latitude'].max())
        min_long = min(min_long, df_ex['longitude'].min())
        max_long = max(max_long, df_ex['longitude'].max())
    
    map = folium.Map(location=[(min_lat + max_lat) / 2, (min_long + max_long) / 2], zoom_start=4, scrollWheelZoom=True, tiles='CartoDB positron')
    
    for index, row in df.iterrows():
        # read files from run summary
        df_ex = pd.read_csv(f'{row.area_name}/{row.file_name}')
    
        # create geojson
        line = LineString(list(zip(df_ex['longitude'], df_ex['latitude'])))
        gdf = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")
                
        coordinates = gdf.to_crs("EPSG:4326")["geometry"].iloc[0].coords.xy
        geojson_coordinates = list(zip(coordinates[0], coordinates[1]))
            
        properties = {col:row[col] for col in df.columns}
        line_color = "[255, 0, 0, 128]" if (lambda x: x['type'] == 'Arrival')(row) else "[0, 0, 255, 128]"
    
            
        geojson_data = {
            'type': 'FeatureCollection',
            'features': [{
                    'type': 'Feature',
                    'id': properties['exercise'],
                    'geometry': {
                    'type': 'LineString',
                    'coordinates': geojson_coordinates,
                    },
                    'properties': properties
                }]
            }
    
                   
        choropleth = folium.Choropleth(
            geo_data=geojson_data,
            data=df,
            columns=('exercise', 'type', 'ship', 'wose_rose_direction', 'wind_speed', 'wrose_current_direction', 'current_velocity'),
            #key_on= 'feature.id',
            line_opacity=0.8,
            highlight=True,
            line_color = 'red' if geojson_data['features'][0]['properties']['type'] == 'Arrival' else 'blue',
            smooth_factor = 1
        )
        choropleth.geojson.add_to(map)    
      
        choropleth.geojson.add_child(
            folium.features.GeoJsonTooltip(['exercise'], labels=False)
        )
            
    st_map = st_folium(map, width=700, height=450, zoom=13, use_container_width=True)
    
    sel_run = ''
    if st_map['last_active_drawing']:
        sel_run = st_map['last_active_drawing']['properties']['exercise']
    
    return sel_run

def main():
    #using full screen
    st.set_page_config(layout="wide", page_title = 'Filter Routes')
    st.markdown(" <style> div[class^='block-container'] { padding-top: 2rem; } </style> ", unsafe_allow_html=True)

    if 'df_runs' in st.session_state:
        #Display Filters and Map
        filtered_df = filter(st.session_state.df_runs, ['type', 'ship', 'wrose_wind_direction', 'wind_speed', 'wrose_current_direction', 'current_velocity'])
        if filtered_df.shape[0]!=0:
            display_map(filtered_df)
        else:
            st.write('No runs found.')

        def highlight_good_practice(row):
            return ['background-color: #E3ECEE' if row['good_practice']==True else '' for col in row]

        st.write(st.session_state.uploaded_comments)

        if st.session_state.uploaded_comments:
            st.dataframe(filtered_df.style.apply(highlight_good_practice, axis=1), column_config={
                "ship": "Ship",
                "trainee": "Trainee",
                "exercise": "Run",
                "type": "Type",
                "wind_speed": "Wind Speed",
                "wind_gust": "Gusting",
                "wrose_wind_direction": "Wind Direction",
                "wind_wave_height": "Wave Height",
                "wind_wave_direction": "Wave Direction",
                "current_velocity": "Current Speed",
                "wrose_current_direction": "Current Direction"
            },
            column_order = ("exercise", "ship", "type", "trainee", "wrose_wind_direction", "wind_speed", "wind_gust", "wrose_current_direction", "current_velocity", "wind_wave_direction", "wind_wave_height"),
            use_container_width=True,
            hide_index=True)
        else:
            st.dataframe(filtered_df, column_config={
                "ship": "Ship",
                "trainee": "Trainee",
                "exercise": "Run",
                "type": "Type",
                "wind_speed": "Wind Speed",
                "wind_gust": "Gusting",
                "wrose_wind_direction": "Wind Direction",
                "wind_wave_height": "Wave Height",
                "wind_wave_direction": "Wave Direction",
                "current_velocity": "Current Speed",
                "wrose_current_direction": "Current Direction"
            },
            column_order = ("exercise", "ship", "type", "trainee", "wrose_wind_direction", "wind_speed", "wind_gust", "wrose_current_direction", "current_velocity", "wind_wave_direction", "wind_wave_height"),
            use_container_width=True,
            hide_index=True)
        #st.session_state.df_runs = filtered_df
    else:
        st.write('Please load the data first.')


if __name__ == "__main__":

    main()