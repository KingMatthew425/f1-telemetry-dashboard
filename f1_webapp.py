import streamlit as st
import matplotlib.pyplot as plt
import fastf1
import os
import numpy as np

# Custom CSS for better design
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        text-align: center;
        padding: 20px;
        background: rgba(0,0,0,0.3);
        border-radius: 10px;
    }
    .stMetric {
        background-color: rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    .stButton>button {
        background: linear-gradient(90deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 12px 30px;
        border-radius: 25px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #ee5a6f 0%, #ff6b6b 100%);
        transform: scale(1.05);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    .stSelectbox label, .sidebar .markdown-text-container {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# Page config
st.set_page_config(page_title="F1 Telemetry Dashboard", layout="wide")

st.title("F1 Vehicle Dynamics Analysis")
st.markdown("*Engineering analysis of Formula 1 telemetry data*")
st.markdown("**A project by Matthew King**")

# Sidebar controls
st.sidebar.header("Race Selection")

YEAR = st.sidebar.selectbox("Year", [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018])

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

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Availability:**")
st.sidebar.info("Most races from 2018-2024 are available. Some 2025 races may still be processing. If you get an error, try a different race/session combination.")

if st.sidebar.button("Check Data Availability"):
    with st.spinner("Checking..."):
        try:
            os.makedirs('f1_cache', exist_ok=True)
            fastf1.Cache.enable_cache('f1_cache')
            test_session = fastf1.get_session(YEAR, RACE, SESSION)
            st.sidebar.success(f"{RACE} {YEAR} {SESSION} data is available!")
        except Exception as e:
            st.sidebar.error(f"Data not available for this combination")

analyze_button = st.sidebar.button("Analyze", type="primary")

if analyze_button:
    with st.spinner("Loading race data... this may take a minute"):
        os.makedirs('f1_cache', exist_ok=True)
        fastf1.Cache.enable_cache('f1_cache')
        
        try:
            session = fastf1.get_session(YEAR, RACE, SESSION)
            session.load()
            
            fastest_lap = session.laps.pick_fastest()
            driver = fastest_lap['Driver']
            lap_time = fastest_lap['LapTime']
            
            telemetry = fastest_lap.get_telemetry()
            
            max_speed = telemetry['Speed'].max()
            min_speed = telemetry['Speed'].min()
            avg_speed = telemetry['Speed'].mean()
            max_rpm = telemetry['RPM'].max()
            
            telemetry['Time_seconds'] = telemetry['Time'].dt.total_seconds()
            
            # FIXED: Convert speed from km/h to m/s for acceleration calculation
            telemetry['Speed_ms'] = telemetry['Speed'] / 3.6
            
            # Calculate acceleration in m/s²
            telemetry['Acceleration'] = telemetry['Speed_ms'].diff() / telemetry['Time_seconds'].diff()
            
            # Clean up any infinite or NaN values from division issues
            telemetry['Acceleration'] = telemetry['Acceleration'].replace([np.inf, -np.inf], np.nan)
            
            # CRITICAL FIX: Remove extreme outliers using percentile method
            # These are data glitches, not real accelerations
            valid_accel = telemetry['Acceleration'].dropna()
            
            if len(valid_accel) > 10:  # Only if we have enough data points
                # Cap at 99th percentile to remove spikes
                p99_accel = valid_accel.quantile(0.99)
                p01_accel = valid_accel.quantile(0.01)
                
                # Also apply hard limits for physical reality
                max_realistic_accel = min(p99_accel, 30)  # 3G max acceleration
                min_realistic_accel = max(p01_accel, -70)  # 7G max braking
                
                telemetry['Acceleration'] = telemetry['Acceleration'].clip(
                    lower=min_realistic_accel, 
                    upper=max_realistic_accel
                )
            
            # Calculate G-forces from cleaned data
            valid_accel = telemetry['Acceleration'].dropna()
            max_accel_g_raw = valid_accel.max() / 9.81 if len(valid_accel) > 0 else 0
            max_decel_g_raw = abs(valid_accel.min()) / 9.81 if len(valid_accel) > 0 else 0
            
            # Cap displayed values at realistic maximums (data can have spikes/glitches)
            max_accel_g = min(max_accel_g_raw, 3.0)  # F1 realistically maxes at ~2.5-3G acceleration
            max_decel_g = min(max_decel_g_raw, 7.0)  # F1 realistically maxes at ~6-7G braking
            
            max_brake_pressure = telemetry['Brake'].max()
            max_throttle = telemetry['Throttle'].max()
            
            st.success("Data loaded successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Driver", driver)
            with col2:
                st.metric("Fastest Lap", str(lap_time).split()[-1])
            with col3:
                st.metric("Max Speed", f"{max_speed:.1f} km/h")
            
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
                st.markdown(f"**Max Speed:** {max_speed:.1f} km/h")
                st.markdown(f"**Min Speed:** {min_speed:.1f} km/h")
                st.markdown(f"**Avg Speed:** {avg_speed:.1f} km/h")
                st.markdown(f"**Max RPM:** {max_rpm:.0f} RPM")
                st.markdown(f"**Max Accel:** {max_accel_g:.2f} G")
                st.markdown(f"**Max Braking:** {max_decel_g:.2f} G")
                st.markdown(f"**Max Brake %:** {max_brake_pressure:.1f}%")
                st.caption("Note: Brake data is often incomplete in F1 telemetry")
                st.markdown(f"**Max Throttle:** {max_throttle:.1f}%")
            
            st.markdown("---")
            st.subheader("Engineering Insights")

            col_insight1, col_insight2 = st.columns(2)

            with col_insight1:
                st.markdown("#### **Braking Performance**")
                st.markdown(f"""
                - **Maximum deceleration:** {max_decel_g:.2f} G ({max_decel_g * 9.81:.1f} m/s²)
                - For context: A road car typically achieves 0.8-1.0 G under emergency braking
                """)
                
                st.markdown("#### **Acceleration Analysis**")
                st.markdown(f"""
                - **Maximum acceleration:** {max_accel_g:.2f} G ({max_accel_g * 9.81:.1f} m/s²)
                - This acceleration requires massive aerodynamic downforce and tire grip
                - Driver experiences force equivalent to **{max_accel_g * 75:.0f} kg** on a 75kg body
                - Peak acceleration occurs at mid-range speeds where downforce is optimized
                """)

            with col_insight2:
                st.markdown("#### **Speed & Power**")
                drag_force = 0.5 * 1.2 * 1.0 * (max_speed/3.6)**2
                estimated_power = drag_force * (max_speed/3.6) / 1000
                st.markdown(f"""
                - **Top speed:** {max_speed:.1f} km/h ({max_speed/1.609:.1f} mph)
                - **Estimated power at top speed:** ~{estimated_power:.0f} kW (~{estimated_power * 1.34:.0f} HP)
                - At this speed, aerodynamic drag is the dominant resistance force
                - Fuel consumption at max speed: ~75-100 kg/hour
                """)
                
                st.markdown("#### **Corner Loading**")
                corner_speed = (min_speed + max_speed) / 2
                st.markdown(f"""
                - **Speed range:** {min_speed:.1f} to {max_speed:.1f} km/h
                - **Minimum corner speed:** {min_speed:.1f} km/h
                - Modern F1 cars generate **3-6 G laterally** in high-speed corners
                - Tire contact patch: ~15cm × 20cm per tire under load
                - Driver neck muscles experience forces equivalent to supporting **{4 * 5:.0f}+ kg** in sustained corners
                """)
            
            # Sector Times and DRS Analysis
            st.markdown("---")
            col_sector, col_drs = st.columns(2)

            with col_sector:
                st.subheader("Sector Times Breakdown")
                st.caption("F1 tracks are divided into 3 sectors. This shows how much time the driver spent in each section of the track.")
                try:
                    sector1 = fastest_lap['Sector1Time']
                    sector2 = fastest_lap['Sector2Time']
                    sector3 = fastest_lap['Sector3Time']
                    
                    s1_sec = sector1.total_seconds() if hasattr(sector1, 'total_seconds') else sector1
                    s2_sec = sector2.total_seconds() if hasattr(sector2, 'total_seconds') else sector2
                    s3_sec = sector3.total_seconds() if hasattr(sector3, 'total_seconds') else sector3
                    
                    total_time = s1_sec + s2_sec + s3_sec
                    
                    st.markdown(f"""
                    **Sector 1:** {s1_sec:.3f}s ({s1_sec/total_time*100:.1f}% of lap)  
                    **Sector 2:** {s2_sec:.3f}s ({s2_sec/total_time*100:.1f}% of lap)  
                    **Sector 3:** {s3_sec:.3f}s ({s3_sec/total_time*100:.1f}% of lap)
                    
                    **Total Lap Time:** {total_time:.3f}s
                    """)
                    
                except Exception as e:
                    st.info("Sector time data not available for this session")

            with col_drs:
                st.subheader("DRS Usage Analysis")
                if 'DRS' in telemetry.columns:
                    drs_active = telemetry['DRS'] > 0
                    drs_distance = telemetry[drs_active]['Distance'].count()
                    total_distance = len(telemetry)
                    drs_percentage = (drs_distance / total_distance) * 100
                    
                    # CHECK IF DRS WAS ACTUALLY USED
                    if drs_distance > 0 and drs_percentage < 95:  # Sanity check: DRS shouldn't be >95% of lap
                        avg_speed_with_drs = telemetry[drs_active]['Speed'].mean()
                        avg_speed_without_drs = telemetry[~drs_active]['Speed'].mean()
                        speed_gain = avg_speed_with_drs - avg_speed_without_drs
                        
                        st.markdown(f"""
                        **DRS Active:** {drs_percentage:.1f}% of lap distance  
                        **Average speed with DRS:** {avg_speed_with_drs:.1f} km/h  
                        **Average speed without DRS:** {avg_speed_without_drs:.1f} km/h  
                        **Estimated speed gain:** {speed_gain:.1f} km/h
                        
                        *DRS (Drag Reduction System) opens the rear wing to reduce drag on designated straights*
                        """)
                        
                        # ONLY PLOT IF DRS WAS USED
                        fig_drs, ax_drs = plt.subplots(figsize=(8, 4))
                        scatter = ax_drs.scatter(telemetry['X'], telemetry['Y'], 
                                                c=telemetry['DRS'], 
                                                cmap='RdYlGn', 
                                                s=15,
                                                alpha=0.6)
                        ax_drs.set_xlabel('X Position (m)')
                        ax_drs.set_ylabel('Y Position (m)')
                        ax_drs.set_title('DRS Zones (Green = Active)')
                        ax_drs.set_aspect('equal')
                        ax_drs.grid(True, alpha=0.3)
                        plt.colorbar(scatter, ax=ax_drs, label='DRS Status')
                        st.pyplot(fig_drs)
                    else:
                        # DRS column exists but no DRS was used
                        st.info("DRS data available but not activated on this lap")
                        st.caption("The fastest lap may have been set while running solo. DRS can only be activated when within 1 second of another car.")
                else:
                    st.info("DRS data not available for this session")
                    st.caption("DRS telemetry is rarely available in the FastF1 data library. Most sessions will not have this data even for Race and Qualifying.")
            
            st.markdown("---")
            st.subheader("Telemetry Analysis")
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
            
            ax1.plot(telemetry['Distance'], telemetry['Speed'], color='red', linewidth=2)
            ax1.set_ylabel('Speed (km/h)')
            ax1.set_title(f'{driver} - Fastest Lap Telemetry')
            ax1.grid(True, alpha=0.3)
            
            ax2.plot(telemetry['Distance'], telemetry['Throttle'], label='Throttle', color='green', linewidth=2)
            ax2.plot(telemetry['Distance'], telemetry['Brake'], label='Brake', color='red', linewidth=2)
            ax2.set_ylabel('Input (%)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
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
            
            # Driver Comparison Section
            st.markdown("---")
            st.subheader("Lap Comparison: Fastest vs Second Fastest")
            st.caption("Comparing the two fastest laps from this session. This shows where time was gained or lost.")
            
            try:
                # Get the two fastest laps
                sorted_laps = session.laps.sort_values('LapTime').head(2)
                
                if len(sorted_laps) >= 2:
                    lap1 = sorted_laps.iloc[0]
                    lap2 = sorted_laps.iloc[1]
                    
                    driver1 = lap1['Driver']
                    driver2 = lap2['Driver']
                    time1 = lap1['LapTime']
                    time2 = lap2['LapTime']
                    
                    time_diff = (time2 - time1).total_seconds()
                    
                    telemetry1 = lap1.get_telemetry()
                    telemetry2 = lap2.get_telemetry()
                    
                    # Add time column
                    telemetry1['Time_seconds'] = telemetry1['Time'].dt.total_seconds()
                    telemetry2['Time_seconds'] = telemetry2['Time'].dt.total_seconds()
                    
                    # Display comparison header
                    col_comp1, col_comp2, col_comp3 = st.columns(3)
                    with col_comp1:
                        st.metric("Fastest Lap", f"{driver1}", f"{str(time1).split()[-1]}")
                    with col_comp2:
                        st.metric("Second Fastest", f"{driver2}", f"{str(time2).split()[-1]}")
                    with col_comp3:
                        st.metric("Time Difference", f"+{time_diff:.3f}s")
                    
                    if driver1 == driver2:
                        st.info(f"Both laps are from {driver1}. Comparing their fastest and second-fastest laps.")
                    else:
                        st.info(f"Comparing {driver1}'s fastest lap against {driver2}'s fastest lap.")
                    
                    # Speed Comparison
                    st.markdown("#### Speed Comparison")
                    fig_comp_speed, ax_comp_speed = plt.subplots(figsize=(14, 6))
                    
                    ax_comp_speed.plot(telemetry1['Distance'], telemetry1['Speed'], 
                                      label=f'{driver1} (Fastest)', color='red', linewidth=2.5)
                    ax_comp_speed.plot(telemetry2['Distance'], telemetry2['Speed'], 
                                      label=f'{driver2} (2nd Fastest)', color='blue', linewidth=2.5, alpha=0.7)
                    
                    ax_comp_speed.set_xlabel('Distance (meters)')
                    ax_comp_speed.set_ylabel('Speed (km/h)')
                    ax_comp_speed.set_title('Speed Trace Comparison')
                    ax_comp_speed.grid(True, alpha=0.3)
                    ax_comp_speed.legend(loc='upper right')
                    
                    st.pyplot(fig_comp_speed)
                    
                    # Throttle and Brake Comparison
                    st.markdown("#### Driver Input Comparison")
                    fig_comp_input, (ax_throttle, ax_brake) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
                    
                    # Throttle comparison
                    ax_throttle.plot(telemetry1['Distance'], telemetry1['Throttle'], 
                                    label=f'{driver1}', color='red', linewidth=2)
                    ax_throttle.plot(telemetry2['Distance'], telemetry2['Throttle'], 
                                    label=f'{driver2}', color='blue', linewidth=2, alpha=0.7)
                    ax_throttle.set_ylabel('Throttle (%)')
                    ax_throttle.set_title('Throttle Application Comparison')
                    ax_throttle.grid(True, alpha=0.3)
                    ax_throttle.legend()
                    
                    # Brake comparison
                    ax_brake.plot(telemetry1['Distance'], telemetry1['Brake'], 
                                 label=f'{driver1}', color='red', linewidth=2)
                    ax_brake.plot(telemetry2['Distance'], telemetry2['Brake'], 
                                 label=f'{driver2}', color='blue', linewidth=2, alpha=0.7)
                    ax_brake.set_xlabel('Distance (meters)')
                    ax_brake.set_ylabel('Brake (Binary: 0=Off, 1=On)')
                    ax_brake.set_title('Brake Application Comparison')
                    ax_brake.grid(True, alpha=0.3)
                    ax_brake.legend()
                    
                    plt.tight_layout()
                    st.pyplot(fig_comp_input)
                    st.caption("Note: FastF1 data library provides brake application as binary (0=off, 1=on) rather than percentage values.")
                    
                    # Statistical Comparison
                    st.markdown("#### Performance Statistics Comparison")
                    col_stats1, col_stats2 = st.columns(2)
                    
                    with col_stats1:
                        st.markdown(f"**{driver1} (Fastest Lap)**")
                        st.markdown(f"Max Speed: {telemetry1['Speed'].max():.1f} km/h")
                        st.markdown(f"Avg Speed: {telemetry1['Speed'].mean():.1f} km/h")
                        st.markdown(f"Min Speed: {telemetry1['Speed'].min():.1f} km/h")
                        st.markdown(f"Max RPM: {telemetry1['RPM'].max():.0f}")
                    
                    with col_stats2:
                        st.markdown(f"**{driver2} (Second Fastest)**")
                        st.markdown(f"Max Speed: {telemetry2['Speed'].max():.1f} km/h")
                        st.markdown(f"Avg Speed: {telemetry2['Speed'].mean():.1f} km/h")
                        st.markdown(f"Min Speed: {telemetry2['Speed'].min():.1f} km/h")
                        st.markdown(f"Max RPM: {telemetry2['RPM'].max():.0f}")
                    
                    # Delta analysis
                    st.markdown("#### Key Differences")
                    speed_delta = telemetry1['Speed'].max() - telemetry2['Speed'].max()
                    avg_speed_delta = telemetry1['Speed'].mean() - telemetry2['Speed'].mean()
                    
                    st.markdown(f"""
                    - **Top speed advantage:** {abs(speed_delta):.1f} km/h in favor of {driver1 if speed_delta > 0 else driver2}
                    - **Average speed advantage:** {abs(avg_speed_delta):.1f} km/h in favor of {driver1 if avg_speed_delta > 0 else driver2}
                    - **Total time difference:** {time_diff:.3f} seconds
                    """)
                    
                else:
                    st.info("Not enough laps available for comparison. Need at least 2 valid laps in this session.")
                    
            except Exception as e:
                st.warning("Lap comparison data not available for this session")
                st.caption("This feature requires at least 2 valid laps with telemetry data")
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.info("Try a different race or session. Some combinations may not have data available.")

else:
    st.info("Select a race and click 'Analyze' to get started")
    st.markdown("""
    ### About This Dashboard
    This tool analyzes Formula 1 telemetry data including:
    - **Speed profiles** around the circuit
    - **Driver inputs** (throttle, brake, gear changes)
    - **Vehicle dynamics** (G-forces, RPM, acceleration)
    - **Lap-by-lap comparisons** between drivers or laps
    
    Data sourced from official F1 timing systems via FastF1 library.
    """)
