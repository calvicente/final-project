import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import LineString, Point
import altair as alt
from vega_datasets import data

def reset_selected_point():
    st.session_state.selected_point = '00:00:01'
    return

def plot_chart(df_ch, column, time, color):

    base = alt.Chart(df_ch).properties(width=550)
    lines = (
        base.mark_line(color=color)
        .encode(x=alt.X('time', title='Time'), y=alt.Y(f"{column}", title=column.replace('_',' ').title()))
    )
    
    xrule = (
        base.mark_rule(color="orange", strokeWidth=2)
        .encode(x=alt.datum(time), size=alt.value(2))
    )

    st.altair_chart(lines + xrule, use_container_width=True) #+ xrule
    return 


def display_map(df, df_ex, color):
    min_lat = df_ex['latitude'].min()
    max_lat = df_ex['latitude'].max()
    min_long = df_ex['longitude'].min()
    max_long = df_ex['longitude'].max()

    map = folium.Map(location=[(min_lat + max_lat) / 2, (min_long + max_long) / 2], zoom_start=st.session_state.zoom_level, scrollWheelZoom=True, tiles='CartoDB positron')
        
    features = []
    fg_points = folium.FeatureGroup(name="Route Points")
    
    for index, row in df_ex.iterrows():
        if row['time'][-1]=='0' or row['time'][-1]=='5':
            # Create a GeoJSON feature for each row
            properties = {col:row[col] for col in df_ex.columns}
            point_geometry = Point(row['longitude'], row['latitude'])
            point_feature = {
                'type': 'Feature',
                'id': row['time'],
                'geometry': point_geometry.__geo_interface__,
                'properties': properties,
            }
    
            features.append(point_feature)
    
        # GeoJSON data for the points
    geojson_data_points = {'type': 'FeatureCollection', 'features': features}

    # Add GeoJSON points to the map
    fg_points.add_child(folium.GeoJson(
            geojson_data_points,
            name='geojson_points',
            marker=folium.Circle(radius=0.5, fill_color=color, fill_opacity=1, color=color, weight=1)
        ))#.add_to(map)

    fg_points.add_child(folium.Marker(
            location = [df_ex[df_ex['time']==st.session_state.selected_point]['latitude'], df_ex[df_ex['time']==st.session_state.selected_point]['longitude']],
            name='selected_point',
            icon=folium.Icon(color='orange', icon='ship', prefix='fa')
        ))

    st_map = st_folium(map, width=700, height=450, zoom=st.session_state.zoom_level, use_container_width=True, feature_group_to_add=fg_points)

    selected_point = st.session_state.selected_point

    if st_map['last_object_clicked'] != st.session_state.last_obj_clicked and st_map['last_object_clicked'] != None:
        selected_point = st_map['last_active_drawing']['properties']['time']
        st.session_state.last_obj_clicked = st_map['last_object_clicked']
    return selected_point

def main():
    #using full screen
    st.set_page_config(layout="wide", page_title = 'Route Analysis')
    st.markdown(" <style> div[class^='block-container'] { padding-top: 2rem; } </style> ", unsafe_allow_html=True)

    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = 13

    if 'selected_point' not in st.session_state:
        st.session_state.selected_point = '00:00:01'
        st.session_state.last_obj_clicked = None


    if 'df_runs' in st.session_state:
    #Display Filters and Map
        #load runs on select box
        if st.session_state.uploaded_comments:
            run_options = [x if y!=True else f"{x}*" for (x,y) in zip(st.session_state.df_runs['exercise'], st.session_state.df_runs['good_practice'])]
        else:
            run_options = [x for x in st.session_state.df_runs['exercise']]
        selected_run = st.sidebar.selectbox('Run:', options = run_options, on_change = reset_selected_point)
        #select run dataframe
        if selected_run:
            filtered_data = st.session_state.df_runs[st.session_state.df_runs['exercise']==selected_run.replace('*','')].to_dict('records')[0]
            color = "red" if filtered_data['type'] == 'Arrival' else "blue"
            df_ex = pd.read_csv(f"{filtered_data['area_name']}/{filtered_data['file_name']}")
            sel_map = display_map(filtered_data, df_ex, color)
            #display run info in the sidebar
            with st.sidebar:
                run_box = st.container(border=True)
                run_box.write(f"Ship: {filtered_data['ship']}  \nType: {filtered_data['type']}  \nTrainee: {filtered_data['trainee']}  \nWind Direction: {filtered_data['wrose_wind_direction']}  \nWind Speed: {filtered_data['wind_speed']}  \nGusting: {filtered_data['wind_gust']}  \nCurrent Direction: {filtered_data['wrose_current_direction']}  \nCurrent Speed: {filtered_data['current_velocity']}  \nWave Direction: {filtered_data['wind_wave_direction']}  \nWave Height: {filtered_data['wind_wave_height']} ")

            #take info from chart or slider
            if sel_map:
                sel_time = st.select_slider("Pick a timeframe:", df_ex['time'].unique(), value = st.session_state.selected_point)
                if sel_map!=st.session_state.selected_point and sel_time == st.session_state.selected_point:
                    st.session_state.selected_point = sel_map
                    sel_time = st.session_state.selected_point
                    st.experimental_rerun()
                elif sel_time !=st.session_state.selected_point and sel_time != sel_map:
                    st.session_state.selected_point = sel_time
                    #sel_map['time'] = sel_time
                    st.experimental_rerun()
                    
            else:
                sel_time = st.select_slider("Pick a timeframe:", df_ex['time'].unique(), value = '00:00:01')
            
            selection = df_ex[df_ex['time']==sel_time].to_dict('records')[0]

            
            
            container_1 = st.container(border=True)

            #show point information
            if selection:
                col1, col2, col3, col4 = container_1.columns(4)
                with col1:
                    st.write(f"**WIND**  \nSpeed: {selection['true_wind_speed']}  \nDirection: {selection['true_wind_direction']}")
                    st.write(f"**CURRENT**  \nSpeed: {selection['current_speed']}  \nDirection: {selection['current_direction']}")
                with col2:
                    st.write(f"**UKC**  \nAft: {selection['under_keel_clearance_aft']}  \nFWd: {selection['under_keel_clearance_fwd']}")
                    st.write(f"**LONGITUDINAL SPEED**  \nSpeed: {selection['longitudinal_speed']}  \nSpeed through water: {selection['longitudinal_speed_through_the_water']}  \n")
                with col3:
                    st.write(f"**ENGINES**  \nStarboard RPM: {selection['starboard_engine_rpm']}  \nPort RPM: {selection['port_engine_rpm']}")
                    st.write(f"**BOW THRUSTER**  \nGained Power: {selection['bow_thruster_gained_power']}  \nPower Order: {selection['bow_thruster_power_order']}")
                with col4:
                    st.write(f"**TRANSVERSE SPEED**  \nAt Ship's Bow: {selection['transverse_speed_at_ships_bow']}  \nAt Ship's Stern: {selection['transverse_speed_at_ships_stern']}  \n")

                #charts
                plot_chart(df_ex, 'sog', sel_time, color)
                plot_chart(df_ex, 'rate_of_turn', sel_time, color)
                plot_chart(df_ex, 'true_wind_speed', sel_time, color)
                plot_chart(df_ex, 'true_wind_direction', sel_time, color)

                #comments
                if st.session_state.uploaded_comments:
                    container_comments = st.container(border=True)
                    with container_comments:
                        st.write(f"**Simulation Scenario:** {filtered_data['simulation_scenario']}")
                        st.write(f"**Manoeuvring Strategy:** {filtered_data['manoeuvring_strategy']}")
                        comments_header = st.container()
                        with comments_header:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write('**Comments**')
                            with col2:
                                st.write('**Is the scenario/strategy still feasible with these conditions?**')
                        nav_comments = st.container()
                        with nav_comments:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write(f"**Navigator:** {filtered_data['navigator_comment']}")
                            with col2:
                                st.write(f"**Navigator:** {filtered_data['still_feasible_navigator']}")
                        pilot_comments = st.container()
                        with pilot_comments:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write(f"**Pilot:** {filtered_data['pilot_comment']}")
                            with col2:
                                st.write(f"**Pilot:** {filtered_data['still_feasible_pilot']}")
                        good_practices_header = st.container()
                        with good_practices_header:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write(f"**List of actions that were or would be good practice for this scenario/strategy:**")
                            with col2:
                                st.write('**Was this simulator run an example of good practice?**')
                        good_practices_comments = st.container()
                        with good_practices_comments:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write(filtered_data['agreed_good_practice'])
                            with col2:
                                st.write(filtered_data['good_practice_example'])
                        run_overview = st.container()
                        with run_overview:
                            st.write('**Overview of the run:**')
                            st.write(filtered_data['overview'])
                else:
                    st.write('No comments csv file selected.')
                    
                    
            else:
                st.write('Please click on the map or move the bar above to see the data.')
               

    else:
        st.write('Please load the data first.')


if __name__ == "__main__":

    main()