import streamlit as st
import matplotlib.pyplot as plt
import fastf1
import os

# Page config
st.set_page_config(page_title="F1 Telemetry Dashboard", layout="wide")

st.title(" F1 Vehicle Dynamics Analysis")
st.markdown("*Engineering analysis of Formula 1 telemetry data*")
st.markdown("**A project by M King**")

# Sidebar controls
st.sidebar.header("Race Selection")

YEAR = st.sidebar.selectbox("Year", [2024, 2023, 2022, 2021, 2020, 2019, 2018])

RACE = st.sidebar.selectbox("Race", [
    'Bahrain', 'Saudi Arabia', 'Australia', 'Japan', 'China',
    'Miami', 'Monaco', 'Spain', 'Canada', 'Austria',
    'Silverstone', 'Hungary', 'Belgium', 'Netherlands', 'Monza',
    'Singapore', 'Austin', 'Mexico', 'Brazil', 'Las Vegas', 'Abu Dhabi'
])

SESSION = st.sidebar.selectbox("Session Type", 
    ['R', 'Q', 'FP1', 'FP2', 'FP3'],
    format_func=lambda x: {'R': 'Race', 'Q': 'Qualifying', 'FP1': 'Practice 1', 
                           'FP2': 'Practice 2', 'FP3': 'Practice 3'}[x]
)

analyze_button = st.sidebar.button(" Analyze", type="primary")

if analyze_button:
    with st.spinner("Loading race data... this may take a minute"):
        # Enable cache
        os.makedirs('f1_cache', exist_ok=True)
        fastf1.Cache.enable_cache('f1_cache')
        
        try:
            # Load race data
            session = fastf1.get_session(YEAR, RACE, SESSION)
            session.load()
            
            # Get fastest lap
            fastest_lap = session.laps.pick_fastest()
            driver = fastest_lap['Driver']
            lap_time = fastest_lap['LapTime']
            
            # Get telemetry
            telemetry = fastest_lap.get_telemetry()
            
            # Calculate metrics
            max_speed = telemetry['Speed'].max()
            min_speed = telemetry['Speed'].min()
            avg_speed = telemetry['Speed'].mean()
            max_rpm = telemetry['RPM'].max()
            
            telemetry['Time_seconds'] = telemetry['Time'].dt.total_seconds()
            telemetry['Acceleration'] = telemetry['Speed'].diff() / telemetry['Time_seconds'].diff()
            max_accel_g = telemetry['Acceleration'].max() / 9.81
            max_decel_g = abs(telemetry['Acceleration'].min()) / 9.81
            
            max_brake_pressure = telemetry['Brake'].max()
            max_throttle = telemetry['Throttle'].max()
            
            # Display results
            st.success(f" Data loaded ")
            
            # Header with key info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Winning Driver", driver)
            with col2:
                st.metric("Fastest Lap", str(lap_time).split()[-1])
            with col3:
                st.metric("Max Speed", f"{max_speed:.1f} km/h")
            
            # Track map and summary
            st.markdown("---")
            col_left, col_right = st.columns([1.5, 1])
            
            with col_left:
                st.subheader("Track Map")
                fig_map, ax_map = plt.subplots(figsize=(10, 8))
                points = ax_map.scatter(telemetry['X'], telemetry['Y'], 
                                      c=telemetry['Speed'], 
                                      cmap='coolwarm', s=20)
                cbar = plt.colorbar(points, ax=ax_map)
                cbar.set_label('Speed (km/h)')
                ax_map.set_xlabel('X Position (m)')
                ax_map.set_ylabel('Y Position (m)')
                ax_map.set_title(f'{driver} - {RACE} {YEAR}')
                ax_map.set_aspect('equal')
                ax_map.grid(True, alpha=0.3)
                st.pyplot(fig_map)
            
            with col_right:
                st.subheader("Performance Metrics")
                metrics_data = {
                    "Metric": ["Max Speed", "Min Speed", "Avg Speed", "Max RPM", 
                              "Max Accel", "Max Braking", "Max Brake %", "Max Throttle"],
                    "Value": [f"{max_speed:.1f} km/h", f"{min_speed:.1f} km/h", 
                             f"{avg_speed:.1f} km/h", f"{max_rpm:.0f} RPM",
                             f"{max_accel_g:.2f} G", f"{max_decel_g:.2f} G",
                             f"{max_brake_pressure:.1f}%", f"{max_throttle:.1f}%"]
                }
                st.table(metrics_data)
            
            # Telemetry charts
            st.markdown("---")
            st.subheader("Telemetry Analysis")
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
            
            # Speed
            ax1.plot(telemetry['Distance'], telemetry['Speed'], color='red', linewidth=2)
            ax1.set_ylabel('Speed (km/h)')
            ax1.set_title(f'{driver} - Fastest Lap Telemetry')
            ax1.grid(True, alpha=0.3)
            
            # Throttle and Brake
            ax2.plot(telemetry['Distance'], telemetry['Throttle'], label='Throttle', color='green', linewidth=2)
            ax2.plot(telemetry['Distance'], telemetry['Brake'], label='Brake', color='red', linewidth=2)
            ax2.set_ylabel('Input (%)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # RPM and Gear
            ax3_gear = ax3.twinx()
            ax3.plot(telemetry['Distance'], telemetry['RPM'], label='RPM', color='purple', linewidth=2)
            ax3_gear.plot(telemetry['Distance'], telemetry['nGear'], label='Gear', color='orange', linewidth=2, linestyle='--')
            ax3.set_xlabel('Distance (meters)')
            ax3.set_ylabel('RPM', color='purple')
            ax3_gear.set_ylabel('Gear', color='orange')
            ax3.grid(True, alpha=0.3)
            ax3.legend(loc='upper left')
            ax3_gear.legend(loc='upper right')
            
            plt.tight_layout()
            st.pyplot(fig)
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.info("Try a different race or session. Some combinations may not have data available.")

else:
    st.info(" Select a race and click 'Analyze' to get started")
    st.markdown("""
    ### 
    This tool analyzes Formula 1 telemetry data including:
    - **Speed profiles** around the circuit
    - **Driver inputs** (throttle, brake, gear changes)
    - **Vehicle dynamics** (G-forces, RPM, acceleration)
    
    Data sourced from official F1 timing systems via FastF1 library.
    """)

