


import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')  # or 'Qt5Agg', depending on what's installed
import board
import busio
import digitalio
from adafruit_max31856 import MAX31856
from datetime import datetime

# Set up SPI and MAX31856 sensors
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs1 = digitalio.DigitalInOut(board.D5)  # Chip select for sensor 1
cs2 = digitalio.DigitalInOut(board.D6)  # Chip select for sensor 2

sensor1 = MAX31856(spi, cs1)
sensor2 = MAX31856(spi, cs2)

# Parameters
interval = 5           # Time interval in seconds
update_interval = 60   # Time interval to update CSV in seconds

# Lists to store time, temperatures, and rates of change
timestamps = []
temperatures_1 = []
temperatures_2 = []
rate_of_change_1 = []
rate_of_change_2 = []

# Create a filename based on the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_data_{current_time}.csv"

# Create an initial empty DataFrame for CSV
columns = ['Time', 'Temperature Sensor 1 (°F)', 'Rate of Change Sensor 1 (°F/s)',
           'Temperature Sensor 2 (°F)', 'Rate of Change Sensor 2 (°F/s)',
           'Average Temperature (°F)', 'Filtered Rate of Change Sensor 1 (°F/s)', 
           'Filtered Rate of Change Sensor 2 (°F/s)', 'Filtered Average Rate of Change (°F/s)']
initial_data = pd.DataFrame(columns=columns)

# Setup for live plotting
plt.ion()  # Turn on interactive mode
fig, axs = plt.subplots(4, 1, figsize=(14, 16))
plt.subplots_adjust(hspace=0.5)

# Live logging and plotting loop
def log_data():
    try:
        last_temp_1 = None
        last_temp_2 = None
        
        while True:
            # Log the current time and temperature from both sensors
            current_time = time.time()
            try:
                current_temp_1 = sensor1.temperature * 9/5 + 32  # Convert to Fahrenheit
                current_temp_2 = sensor2.temperature * 9/5 + 32  # Convert to Fahrenheit
            except Exception as e:
                print(f"Error reading temperatures: {e}")
                continue  # Skip to the next iteration if there's an error

            # Append data to lists
            timestamps.append(current_time)
            temperatures_1.append(current_temp_1)
            temperatures_2.append(current_temp_2)

            # Calculate rate of change for each sensor
            if last_temp_1 is not None:
                change_1 = current_temp_1 - last_temp_1
                rate_of_change_1.append(change_1 / interval)
            else:
                rate_of_change_1.append(0)

            if last_temp_2 is not None:
                change_2 = current_temp_2 - last_temp_2
                rate_of_change_2.append(change_2 / interval)
            else:
                rate_of_change_2.append(0)

            # Update last temperatures
            last_temp_1 = current_temp_1
            last_temp_2 = current_temp_2

            # Wait for the specified interval
            time.sleep(interval)

            # Check if it's time to update the CSV file
            if len(timestamps) % update_interval == 0:
                df = pd.DataFrame({
                    'Time': pd.to_datetime(timestamps, unit='s'),
                    'Temperature Sensor 1 (°F)': temperatures_1,
                    'Rate of Change Sensor 1 (°F/s)': rate_of_change_1,
                    'Temperature Sensor 2 (°F)': temperatures_2,
                    'Rate of Change Sensor 2 (°F/s)': rate_of_change_2
                })

                # Calculate average temperature
                df['Average Temperature (°F)'] = (df['Temperature Sensor 1 (°F)'] + df['Temperature Sensor 2 (°F)']) / 2
                
                # Calculate filtered rate of change from the last minute
                df['Filtered Rate of Change Sensor 1 (°F/s)'] = df['Rate of Change Sensor 1 (°F/s)'].rolling(window=12).mean().fillna(0)
                df['Filtered Rate of Change Sensor 2 (°F/s)'] = df['Rate of Change Sensor 2 (°F/s)'].rolling(window=12).mean().fillna(0)
                df['Filtered Average Rate of Change (°F/s)'] = (df['Filtered Rate of Change Sensor 1 (°F/s)'] + df['Filtered Rate of Change Sensor 2 (°F/s)']) / 2

                # Append to CSV file
                df.to_csv(filename, mode='a', header=not bool(len(timestamps)), index=False)



# Setup for live plotting
plt.ion()  # Turn on interactive mode
fig, axs = plt.subplots(4, 1, figsize=(14, 16))
plt.subplots_adjust(hspace=0.5)

    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
        plt.ioff()  # Turn off interactive mode
        plt.show()  # Show the final plots

def update_plots(df):
    # Clear previous plots
    for ax in axs:
        ax.cla()

    # Determine y-axis limits based on current data
    min_temp = min(min(temperatures_1, default=0), min(temperatures_2, default=0)) - 5
    max_temp = max(max(temperatures_1, default=0), max(temperatures_2, default=0)) + 5
    min_rate = min(min(rate_of_change_1, default=0), min(rate_of_change_2, default=0)) - 0.5
    max_rate = max(max(rate_of_change_1, default=0), max(rate_of_change_2, default=0)) + 0.5

    # Ensure lengths match for plotting
    plot_timestamps = pd.to_datetime(timestamps, unit='s')

    # Plot 1: Total Temperature vs. Time
    axs[0].plot(plot_timestamps, temperatures_1, label='Sensor 1 (°F)', color='tab:red')
    axs[0].plot(plot_timestamps, temperatures_2, label='Sensor 2 (°F)', color='tab:orange')
    axs[0].set_title('Total Temperature Data from Thermocouples')
    axs[0].set_xlabel('Time')
    axs[0].set_ylabel('Temperature (°F)')
    axs[0].set_ylim(min_temp, max_temp)
    axs[0].legend()
    axs[0].grid()

    # Plot 2: Rate of Change vs. Time
    axs[1].plot(plot_timestamps, rate_of_change_1, label='Rate of Change Sensor 1 (°F/s)', color='tab:red')
    axs[1].plot(plot_timestamps, rate_of_change_2, label='Rate of Change Sensor 2 (°F/s)', color='tab:orange')
    axs[1].set_title('Rate of Change of Temperature')
    axs[1].set_xlabel('Time')
    axs[1].set_ylabel('Rate of Change (°F/s)')
    axs[1].set_ylim(min_rate, max_rate)
    axs[1].legend()
    axs[1].grid()

    # Plot 3: Filtered Rate of Change vs. Time
    axs[2].plot(plot_timestamps, df['Filtered Rate of Change Sensor 1 (°F/s)'], label='Filtered Rate of Change Sensor 1 (°F/s)', color='tab:red')
    axs[2].plot(plot_timestamps, df['Filtered Rate of Change Sensor 2 (°F/s)'], label='Filtered Rate of Change Sensor 2 (°F/s)', color='tab:orange')
    axs[2].set_title('Filtered Rate of Change of Temperature')
    axs[2].set_xlabel('Time')
    axs[2].set_ylabel('Filtered Rate of Change (°F/s)')
    axs[2].set_ylim(min_rate, max_rate)
    axs[2].legend()
    axs[2].grid()

    # Plot 4: Average Temperature vs. Time
    axs[3].plot(plot_timestamps, df['Average Temperature (°F)'], label='Average Temperature (°F)', color='tab:green')
    axs[3].set_title('Average Temperature Over Time')
    axs[3].set_xlabel('Time')
    axs[3].set_ylabel('Average Temperature (°F)')
    axs[3].set_ylim(min_temp, max_temp)
    axs[3].legend()
    axs[3].grid()

    plt.draw()
    plt.pause(0.01)  # Adjust this value if needed for better performance


# Start logging data
log_data()
