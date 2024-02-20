import pandas as pd
pd.options.display.max_columns = None
pd.options.display.max_rows = None
import easygui
import csv
import geopy.distance
import os
import numpy as np
import streamlit as st
import tempfile


wind_rose = {'N1':[348.76, 360], 'N2':[0, 11.25], 'NNE':[11.26, 33.75], 'NE':[33.76, 56.25], 'ENE':[56.26, 78.75], 'E':[78.76, 101.25], 'ESE':[101.26, 123.75], 'SE':[123.76, 146.25], 'SSE':[146.26, 168.75], 'S':[168.76, 191.25], 'SSW':[191.26, 213.75], 'SW':[213.76, 236.25], 'WSW':[236.26, 258.75], 'W':[258.76, 281.25], 'WNW':[281.26, 303.75], 'NW':[303.76, 326.25], 'NNW':[326.26, 348.75]}


#uses wind_rose dict to get direction
def degrees_to_direction(degrees):
    for direction, angle_range in wind_rose.items():
        if angle_range[0] <= degrees <= angle_range[1]:
            if (direction=='N1') or (direction=='N2'):
                return 'N'
            else:
                return direction
    return None

#gets run information from excel file  
def get_file_info(file_name):
    with open(file_name, 'r') as file:
        my_reader = csv.reader(file, delimiter=',')
        lst_my_reader = list(my_reader)
    
    ship_name = str(lst_my_reader[0]).split('OS: ')[1].replace("']",'')
    trainee = str(lst_my_reader[1]).split('Trainee: ')[1].replace("']",'')
    ex_name = str(lst_my_reader[2]).split('Exercise name: ')[1].replace(".nti']",'')
    area = str(lst_my_reader[3]).split('Area: ')[1].replace("']",'')
    ex_start_time = str(lst_my_reader[4]).split('Exercise start time: ')[1].replace("']",'')
    ex_date = str(lst_my_reader[5]).split('Exercise date: ')[1].replace("']",'')
    model_vers = str(lst_my_reader[7]).split('Model version: ')[1].replace("']",'')

    dict_info = {'ship':ship_name, 'trainee':trainee, 'exercise':ex_name, 'area_name':area, 'exercise_start_time':ex_start_time, 'exercise_date':ex_date, 'ship_model_version':model_vers}
    
    return dict_info

#creates summary file with information from all runs
def create_summary(loaded_files):
    log_files = [n for n in loaded_files if 'Log-' in n]
    ship_files = [n for n in loaded_files if 'ShipDynamics' in n]
    
    df_all_runs = pd.DataFrame()
    
    #iterate files
    for log, ship in zip(log_files, ship_files):
        
        #check if files come from the same exercise
        if log.replace('Log-','') == ship.replace('ShipDynamics-',''):
    
            #if yes, read the csvs and create dataframes
            log_df = pd.read_csv(log, sep=',', header=8)
            ship_df = pd.read_csv(ship, sep=',', header=8)
    
            #merge files
            df_merged = pd.merge(ship_df, log_df, on='time', suffixes=('_df1', '_df2'))
    
            #drop common columns
            common_columns = [col for col in df_merged.columns if col.endswith('_df2')]
            df_merged = df_merged.drop(common_columns, axis=1)
            df_merged = df_merged.drop(['Local position X', 'Local position Y'], axis=1)
    
            #drop first rows (units)
            df_merged.drop([0,1], inplace=True)
    
            #rename columns
            df_merged.columns = [c.replace('_df1','').replace(' ','_').replace("'",'').lower() for c in df_merged.columns]
    
            #change numeric columns to float
            columns_float = df_merged.drop(['time', 'autopilot_state'], axis=1).columns
            df_merged['distance_made_good'] = df_merged['distance_made_good'].str.replace(',','')
            for column in columns_float:
                df_merged[column] = df_merged[column].astype(float)
    
            #get file info
            finfo = get_file_info(log)
    
            #arrival or departure
            dist_start = geopy.distance.geodesic((port_lat,port_long), (df_merged.iloc[0]['latitude'], df_merged.iloc[0]['longitude'])).m
            dist_end = geopy.distance.geodesic((port_lat,port_long), (df_merged.iloc[-1]['latitude'], df_merged.iloc[-1]['longitude'])).m
            if dist_start>dist_end:
                finfo['type'] = 'Arrival'
            else:
                finfo['type'] = 'Departure'
    
            #create wind rose column
            df_merged['wrose_wind_direction'] = df_merged['true_wind_direction'].apply(degrees_to_direction)
           
            #get wind speed
            wmax = df_merged['true_wind_speed'].max()
            wmin = df_merged['true_wind_speed'].min()
            diff = int(wmax-wmin)

            finfo['wind_speed'] = int(df_merged['true_wind_speed'].mean())
            finfo['wind_gust'] = 0 if finfo['wind_speed']== 0 else (finfo['wind_speed'] + 5)

            #wind
            finfo['wind_direction'] = int(df_merged['true_wind_direction'].mean())
            if finfo['wind_speed'] == 0:
                finfo['wrose_wind_direction'] = 'N/A'
            else:
                finfo['wrose_wind_direction'] = str(list(dict(df_merged['wrose_wind_direction'].value_counts(sort=False)).keys())).replace(',','-').replace("'",'').replace('[','').replace(']','')
           
            #wave
            finfo['wind_wave_height'] = str(list(dict(df_merged['significant_wave_height'].value_counts(sort=False)).keys())).replace(',',' -').replace("'",'').replace('[','').replace(']','')
            finfo['wind_wave_direction'] = str(list(dict(df_merged['wave_direction'].value_counts(sort=False)).keys())).replace(',',' -').replace("'",'').replace('[','').replace(']','')
    
            #current
            finfo['current_location'] = f'{curr_lat}, {curr_long}'
            #get closest point to current measurement point
            def calculate_distance(row):
                return geopy.distance.geodesic((row['latitude'], row['longitude']), (curr_lat, curr_long)).m
            df_merged['distance'] = df_merged.apply(calculate_distance, axis=1)
            closest_point = df_merged.loc[df_merged['distance'].idxmin()]
            #get values
            finfo['current_velocity'] = closest_point['current_speed']
            finfo['current_direction'] = closest_point['current_direction']
            finfo['wrose_current_direction'] = degrees_to_direction(closest_point['current_direction'])
    
    
            #save modified csv
            dir = f"./{finfo['area_name']}"
            if not os.path.exists(dir):
                os.mkdir(dir)
            finfo['file_name'] = f"{finfo['area_name']} {finfo['exercise']}.csv"
    
            df_merged.drop('distance', axis=1).to_csv(f"{dir}/{finfo['file_name']}")
            
            #add to all runs
            df_all_runs = pd.concat([df_all_runs, pd.DataFrame([finfo])], ignore_index=True)
        
    if uploaded_comments:
        comments = pd.read_csv(uploaded_comments, sep=';')
        df_all_runs = pd.merge(df_all_runs, comments, on='exercise')
    
    
    #save
    df_all_runs.to_csv(f"{dir}/Runs Summary.csv")
    return df_all_runs
    
#using full screen
st.set_page_config(layout="wide", page_title = "Load Data")
st.markdown(" <style> div[class^='block-container'] { padding-top: 2rem; } </style> ", unsafe_allow_html=True)

st.title(':red[**LogWise**]')

if "last_object_clicked" not in st.session_state:
    st.session_state["last_object_clicked"] = None

#reading files

if 'loaded_files' not in st.session_state:
    st.write('Please load the data to start:')
    uploaded_files = st.file_uploader("Please select OS and Ship Dynamics log files to be displayed:", type='csv', accept_multiple_files = True)
    uploaded_comments = st.file_uploader("Please select comments file:", type='csv', accept_multiple_files = False)
    
    files_list = []
    temp_dir = tempfile.mkdtemp()


    if uploaded_comments:
                path = os.path.join(temp_dir, uploaded_comments.name)
                with open(path, "wb") as f:
                        f.write(uploaded_comments.getvalue())
                st.session_state.uploaded_comments = True
    else:
        st.session_state.uploaded_comments = False
    
    if len(uploaded_files)!=0: 
        if len(uploaded_files) % 2 == 0:
            for uploaded_file in uploaded_files:
                if uploaded_file:
                        path = os.path.join(temp_dir, uploaded_file.name)
                        with open(path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                files_list.append(path)
    
            with st.form("Settings", clear_on_submit=False):
                st.write("Please inform:")
                port_lat = st.text_input('Port latitude in decimal degrees:', '')
                port_long = st.text_input('Port longitude in decimal degrees:', '')
                curr_lat = st.text_input('Please enter current measurement point latitude in decimal degrees:', '')
                curr_long = st.text_input('Please enter current measurement point longitude in decimal degrees:', '')

         
                submitted = st.form_submit_button("Submit")
                if submitted:
                    if port_lat=='' :
                        st.error('Please inform port latitude')
                    elif port_long=='' :
                        st.error('Please inform port longitude')
                    elif curr_lat=='' :
                        st.error('Please inform current latitude')
                    elif curr_long=='' :
                        st.error('Please inform current longitude')
                    else:
                        with st.spinner('Please wait...'):
                            df_runs = create_summary(files_list)
                        st.write('Files loaded! You can navigate through the other tabs now.')
                        st.session_state.df_runs = df_runs
                        st.session_state.df_initial = df_runs
                        st.session_state.loaded_files = True
    
        else:
            st.warning("It's necessary to add both OS and Ship Dynamics files for each run.")
            
    
    
            
else:
    st.write('The data is loaded, you can explore the other tabs. To upload other files, please update the browser.')

#port_lat 51.116124 dover
#port_long 1.319884 dover
#curr_lat 51.107442 dover
#curr_long 1.338515 dover