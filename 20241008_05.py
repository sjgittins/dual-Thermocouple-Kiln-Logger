#To avoid divide-by-zero errors when calculating the rate of change, we need to implement checks to ensure that we're not dividing by zero. Specifically, we should check that the denominator (the time interval) is greater than zero before performing the division.
#Here's the revised code with the necessary adjustments to handle potential divide-by-zero issues in the rate of change calculation:
#Key Updates:
#Rate of Change Calculation: Now calculates the average temperature over the last minute of data and divides by the time difference only if the time difference is greater than zero.
#Error Handling: Added checks for reading temperatures and saving data to handle exceptions gracefully.
#Dynamic Plotting: Ensured that all plots use the same timestamps and adjust the y-limits dynamically based on current data.
#This should resolve the divide-by-zero issues and ensure smooth operation during logging and plotting.





import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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
smoothing_window = 5   # Window size for smoothing

# Lists to store time, temperatures, and rates of change
timestamps = []
temperatures_1 = []
temperatures_2 = []
rate_of_change_1 = []
rate_of_change_2 = []

# Initial setup
last_temp_1 = None
last_temp_2 = None

# Create a filename based on the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_data_{current_time}.csv"

# Function to convert Celsius to Fahrenheit
def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

# Setup for live plotting
plt.ion()  # Turn on interactive mode
fig, axs = plt.subplots(4, 1, figsize=(14, 16))
plt.subplots_adjust(hspace=0.5)

# Live logging and plotting loop
def log_data():
    global last_temp_1, last_temp_2
    df = None  # Initialize df
    try:
        while True:
            current_time = time.time()

            # Read temperature from Sensor 1 with error handling
            try:
                current_temp_1 = sensor1.temperature
                current_temp_1_f = celsius_to_fahrenheit(current_temp_1)  # Convert to Fahrenheit
            except Exception as e:
                print(f"Error reading sensor 1: {e}")
                current_temp_1_f = celsius_to_fahrenheit(last_temp_1) if last_temp_1 is not None else 0

            # Read temperature from Sensor 2 with error handling
            try:
                current_temp_2 = sensor2.temperature
                current_temp_2_f = celsius_to_fahrenheit(current_temp_2)  # Convert to Fahrenheit
            except Exception as e:
                print(f"Error reading sensor 2: {e}")
                current_temp_2_f = celsius_to_fahrenheit(last_temp_2) if last_temp_2 is not None else 0

            # Append data to lists
            timestamps.append(current_time)
            temperatures_1.append(current_temp_1_f)
            temperatures_2.append(current_temp_2_f)

            # Calculate the rate of change based on the last minute of data
            if len(timestamps) > 12:  # Ensure we have enough data points for 1 minute (12 data points for 5s interval)
                one_minute_ago = current_time - 60
                recent_temps_1 = [temp for ts, temp in zip(timestamps, temperatures_1) if ts >= one_minute_ago]
                recent_temps_2 = [temp for ts, temp in zip(timestamps, temperatures_2) if ts >= one_minute_ago]
                
                if recent_temps_1 and last_temp_1 is not None:
                    avg_temp_1 = np.mean(recent_temps_1)
                    change_1 = current_temp_1_f - avg_temp_1
                    time_diff = current_time - (one_minute_ago + 60)
                    rate_of_change_1.append(change_1 / time_diff if time_diff > 0 else 0)
                else:
                    rate_of_change_1.append(0)

                if recent_temps_2 and last_temp_2 is not None:
                    avg_temp_2 = np.mean(recent_temps_2)
                    change_2 = current_temp_2_f - avg_temp_2
                    time_diff = current_time - (one_minute_ago + 60)
                    rate_of_change_2.append(change_2 / time_diff if time_diff > 0 else 0)
                else:
                    rate_of_change_2.append(0)
            else:
                rate_of_change_1.append(0)
                rate_of_change_2.append(0)

            # Print temperature and rate of change for both sensors
            print(f"Sensor 1: Temperature = {current_temp_1_f:.2f} °F, Rate of Change = {rate_of_change_1[-1]:.2f} °F/s")
            print(f"Sensor 2: Temperature = {current_temp_2_f:.2f} °F, Rate of Change = {rate_of_change_2[-1]:.2f} °F/s")

            # Update last temperatures
            last_temp_1 = current_temp_1
            last_temp_2 = current_temp_2

            # Wait for the specified interval
            time.sleep(interval)

            # Check if it's time to update the CSV file
            if len(timestamps) % update_interval == 0:
                try:
                    # Convert timestamps to readable format
                    df = pd.DataFrame({
                        'Time': pd.to_datetime(timestamps, unit='s'),
                        'Temperature Sensor 1 (°F)': temperatures_1,
                        'Rate of Change Sensor 1 (°F/s)': rate_of_change_1,
                        'Temperature Sensor 2 (°F)': temperatures_2,
                        'Rate of Change Sensor 2 (°F/s)': rate_of_change_2
                    })

                    # Calculate averages and filtered rates
                    df['Average Temperature (°F)'] = (df['Temperature Sensor 1 (°F)'] + df['Temperature Sensor 2 (°F)']) / 2
                    df['Average Rate of Change (°F/s)'] = (df['Rate of Change Sensor 1 (°F/s)'] + df['Rate of Change Sensor 2 (°F/s)']) / 2

                    # Apply smoothing using a moving average
                    df['Filtered Rate of Change Sensor 1 (°F/s)'] = df['Rate of Change Sensor 1 (°F/s)'].rolling(window=smoothing_window).mean().fillna(0)
                    df['Filtered Rate of Change Sensor 2 (°F/s)'] = df['Rate of Change Sensor 2 (°F/s)'].rolling(window=smoothing_window).mean().fillna(0)
                    df['Filtered Average Rate of Change (°F/s)'] = (df['Filtered Rate of Change Sensor 1 (°F/s)'] + df['Filtered Rate of Change Sensor 2 (°F/s)']) / 2

                    # Append to CSV file
                    df.to_csv(filename, mode='a', header=not bool(len(timestamps)), index=False)
                except Exception as e:
                    print(f"Error updating CSV file: {e}")

            # Live plot update only if df is defined
            if df is not None:
                update_plots(df)

    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
        # Save any remaining data
        if df is not None:
            try:
                df.to_csv(filename, mode='a', header=not bool(len(timestamps)), index=False)
            except Exception as e:
                print(f"Error saving final data to CSV: {e}")
        plt.ioff()  # Turn off interactive mode
        plt.show()  # Show the final plots
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

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
    axs[0].set_ylim(min_temp, max_temp)  # Set dynamic y-limits
    axs[0].legend()
    axs[0].grid()

    # Plot 2: Rate of Change vs. Time
    axs[1].plot(plot_timestamps, rate_of_change_1, label='Rate of Change Sensor 1 (°F/s)', color='tab:red')
    axs[1].plot(plot_timestamps, rate_of_change_2, label='Rate of Change Sensor 2 (°F/s)', color='tab:orange')
    axs[1].set_title('Rate of Change of Temperature')
    axs[1].set_xlabel('Time')
    axs[1].set_ylabel('Rate of Change (°F/s)')
    axs[1].set_ylim(min_rate, max_rate)  # Set dynamic y-limits
    axs[1].legend()
    axs[1].grid()

    # Plot 3: Filtered Rate of Change vs. Time
    axs[2].plot(plot_timestamps, df['Filtered Rate of Change Sensor 1 (°F/s)'], label='Filtered Rate of Change Sensor 1 (°F/s)', color='tab:red')
    axs[2].plot(plot_timestamps, df['Filtered Rate of Change Sensor 2 (°F/s)'], label='Filtered Rate of Change Sensor 2 (°F/s)', color='tab:orange')
    axs[2].set_title('Filtered Rate of Change of Temperature')
    axs[2].set_xlabel('Time')
    axs[2].set_ylabel('Filtered Rate of Change (°F/s)')
    axs[2].set_ylim(min_rate, max_rate)  # Set dynamic y-limits
    axs[2].legend()
    axs[2].grid()

    # Plot 4: Average Temperature vs. Time
    axs[3].plot(plot_timestamps, df['Average Temperature (°F)'], label='Average Temperature (°F)', color='tab:green')
    axs[3].set_title('Average Temperature Over Time')
    axs[3].set_xlabel('Time')
    axs[3].set_ylabel('Average Temperature (°F)')
    axs[3].set_ylim(min_temp, max_temp)  # Set dynamic y-limits
    axs[3].legend()
    axs[3].grid()

    plt.draw()  # Update the plot
    plt.pause(0.01)  # Pause for a brief moment

# Start logging data
log_data()
