import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import board
import busio
import digitalio
import adafruit_max31856 
from datetime import datetime
import logging
import pytz
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up SPI and MAX31856 sensors
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs1 = digitalio.DigitalInOut(board.D5)  # Chip select for sensor 1
cs1.direction = digitalio.Direction.OUTPUT
cs2 = digitalio.DigitalInOut(board.D16)  # Chip select for sensor 2
cs2.direction = digitalio.Direction.OUTPUT

sensor1 = adafruit_max31856.MAX31856(spi, cs1)
sensor2 = adafruit_max31856.MAX31856(spi, cs2)

# Parameters
interval = 10           # Time interval in seconds
update_interval = 60    # Time interval to update CSV in seconds
smoothing_window = 20   # Updated smoothing window size for moving average
max_timeout_intervals = 3  # Timeout after 3 intervals (30 seconds)

# Create a filename based on the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_data_{current_time}.csv"

# Initialize DataFrame
columns = ['Time', 'Temperature Sensor 1 (°F)', 'Rate of Change Sensor 1 (°F/h)',
           'Temperature Sensor 2 (°F)', 'Rate of Change Sensor 2 (°F/h)',
           'Average Temperature (°F)', 'Moving Average Rate of Change Sensor 1 (°F/h)', 
           'Moving Average Rate of Change Sensor 2 (°F/h)', 'Average Rate of Change (°F/h)']  
data_df = pd.DataFrame(columns=columns)

# Setup for live plotting
plt.ion()
fig, axs = plt.subplots(3, 1, figsize=(10, 7))
plt.subplots_adjust(hspace=0.3)

def validate_data(current_temp_1, current_temp_2, last_temp_1, last_temp_2):
    """
    Validates the temperature data to ensure no unreasonable fluctuations.
    Returns False if data is invalid.
    """
    if last_temp_1 is not None and abs(current_temp_1 - last_temp_1) >= 500:
        logging.warning(f"Temperature Sensor 1: Change exceeds limit. Skipping this reading: {current_temp_1}°F (last: {last_temp_1}°F)")
        return False
    if last_temp_2 is not None and abs(current_temp_2 - last_temp_2) >= 500:
        logging.warning(f"Temperature Sensor 2: Change exceeds limit. Skipping this reading: {current_temp_2}°F (last: {last_temp_2}°F)")
        return False

    if not (-100 <= current_temp_1 <= 3000 and -100 <= current_temp_2 <= 3000):
        logging.warning("Temperature out of range. Skipping this reading.")
        return False

    return True

def log_data():
    last_temp_1, last_temp_2 = None, None
    last_write_time = time.time()  # Keep track of the last time we wrote to the CSV
    sensor1_last_response = time.time()
    sensor2_last_response = time.time()

    # Create the CSV file with headers initially
    data_df.to_csv(filename, mode='w', header=True, index=False)

    try:
        while True:
            current_time = time.time()
            try:
                current_temp_1 = sensor1.temperature * 9/5 + 32  # Convert to Fahrenheit
                current_temp_2 = sensor2.temperature * 9/5 + 32  # Convert to Fahrenheit

                # Update last response time for each sensor
                if current_temp_1 is not None:
                    sensor1_last_response = current_time
                if current_temp_2 is not None:
                    sensor2_last_response = current_time
                
                # Validate the data before appending
                if not validate_data(current_temp_1, current_temp_2, last_temp_1, last_temp_2):
                    continue

            except Exception as e:
                logging.error(f"Error reading temperatures: {e}")
                continue

            # Append data to DataFrame with local time
            local_time = datetime.fromtimestamp(current_time, pytz.timezone('America/New_York'))
            rate_of_change_1 = (current_temp_1 - last_temp_1) / interval * 3600 if last_temp_1 is not None else 0
            rate_of_change_2 = (current_temp_2 - last_temp_2) / interval * 3600 if last_temp_2 is not None else 0
            average_rate_of_change = (rate_of_change_1 + rate_of_change_2) / 2  # Average rate of change

            data_df.loc[len(data_df)] = [
                local_time,
                current_temp_1,
                rate_of_change_1,
                current_temp_2,
                rate_of_change_2,
                (current_temp_1 + current_temp_2) / 2,
                0,  # Placeholder for moving average
                0,  # Placeholder for moving average
                average_rate_of_change  # New column value
            ]

            last_temp_1, last_temp_2 = current_temp_1, current_temp_2
            time.sleep(interval)

            # Calculate moving averages before updating CSV
            if len(data_df) >= smoothing_window:
                data_df['Moving Average Rate of Change Sensor 1 (°F/h)'] = data_df['Rate of Change Sensor 1 (°F/h)'].rolling(window=smoothing_window).mean()
                data_df['Moving Average Rate of Change Sensor 2 (°F/h)'] = data_df['Rate of Change Sensor 2 (°F/h)'].rolling(window=smoothing_window).mean()

            # Check if it's time to update the CSV file based on time elapsed
            if time.time() - last_write_time >= update_interval:
                try:
                    data_df.to_csv(filename, mode='a', header=False, index=False)
                    last_write_time = time.time()  # Update the timestamp
                except Exception as e:
                    logging.error(f"Error writing to CSV: {e}")

            # Update plots
            update_plots(data_df, sensor1_last_response, sensor2_last_response)

    except KeyboardInterrupt:
        logging.info("Logging stopped by user.")
        
        # Save and show the plots
        plt.ioff()  # Turn off interactive mode
        plt.savefig(f"temperature_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")  # Save the plot
        plt.show()  # Show the final plots
        cleanup()

def update_plots(df, sensor1_last_response, sensor2_last_response):
    # Clear previous plots
    for ax in axs:
        ax.cla()

    # Limit number of data points to plot (last 500 points)
    max_points = 500
    plot_data = df.tail(max_points)

    # Check for empty DataFrame
    if plot_data.empty:
        return

    # Last data points
    last_temp1 = plot_data['Temperature Sensor 1 (°F)'].iloc[-1]
    last_temp2 = plot_data['Temperature Sensor 2 (°F)'].iloc[-1]
    
    # Set consistent limits for y-axis
    min_temp = plot_data[['Temperature Sensor 1 (°F)', 'Temperature Sensor 2 (°F)']].min().min() - 5
    max_temp = plot_data[['Temperature Sensor 1 (°F)', 'Temperature Sensor 2 (°F)']].max().max() + 5

    axs[0].plot(plot_data['Time'], plot_data['Temperature Sensor 1 (°F)'], label='Sensor 1')
    axs[0].plot(plot_data['Time'], plot_data['Temperature Sensor 2 (°F)'], label='Sensor 2')
    axs[0].set_title('Temperature vs Time')
    axs[0].set_xlabel('Time')
    axs[0].set_ylabel('Temperature (°F)')
    axs[0].legend()
    axs[0].set_ylim(min_temp, max_temp)

    # Check for timeouts and show error message
    sensor1_timeout = time.time() - sensor1_last_response > max_timeout_intervals * interval
    sensor2_timeout = time.time() - sensor2_last_response > max_timeout_intervals * interval

    if sensor1_timeout:
        axs[0].text(0.5, 0.9, f"ERROR: Sensor 1 timeout {int(time.time() - sensor1_last_response)}s", 
                    transform=axs[0].transAxes, color='red', fontsize=12, ha='center')
    if sensor2_timeout:
        axs[0].text(0.5, 0.8, f"ERROR: Sensor 2 timeout {int(time.time() - sensor2_last_response)}s", 
                    transform=axs[0].transAxes, color='red', fontsize=12, ha='center')

    plt.draw()

def cleanup():
    plt.close()

log_data()  # Start logging and plotting
