#functioning decently.  wish I could keep plotting since t=0 but concerns about memory.  perhaps I can push to something web based and do the plotting

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

print('Sensor1', sensor1.temperature, 'deg F')
print('Sensor2', sensor2.temperature, 'deg F')

# Read and print faults
faults = sensor1.fault
print("Sensor 1 Faults - D5:")
for fault_type, fault_value in faults.items():
    print(f"{fault_type}: {fault_value}")

faults = sensor2.fault
print("Sensor 2 Faults - D16:")
for fault_type, fault_value in faults.items():
    print(f"{fault_type}: {fault_value}")

# Parameters
interval = 5           # Time interval in seconds
update_interval = 60   # Time interval to update CSV in seconds
smoothing_window = 20  # Updated smoothing window size for moving average

# Create a filename based on the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_data_{current_time}.csv"

# Initialize DataFrame
columns = ['Time', 'Temperature Sensor 1 (°F)', 'Rate of Change Sensor 1 (°F/h)',
           'Temperature Sensor 2 (°F)', 'Rate of Change Sensor 2 (°F/h)',
           'Average Temperature (°F)', 'Moving Average Rate of Change Sensor 1 (°F/h)', 
           'Moving Average Rate of Change Sensor 2 (°F/h)', 'Average Rate of Change (°F/h)']  # Updated column names
data_df = pd.DataFrame(columns=columns)

# Setup for live plotting
plt.ion()
fig, axs = plt.subplots(3, 1, figsize=(14, 12))
plt.subplots_adjust(hspace=0.5)

def log_data():
    last_temp_1, last_temp_2 = None, None

    # Create the CSV file with headers initially
    data_df.to_csv(filename, mode='w', header=True, index=False)

    try:
        while True:
            current_time = time.time()
            try:
                current_temp_1 = sensor1.temperature * 9/5 + 32  # Convert to Fahrenheit
                current_temp_2 = sensor2.temperature * 9/5 + 32  # Convert to Fahrenheit
                
                # Data validation: Check if temperatures are within a reasonable range
                if last_temp_1 is not None and abs(current_temp_1 - last_temp_1) >= 500:
                    logging.warning(f"Temperature Sensor 1: Change exceeds limit. Skipping this reading: {current_temp_1}°F (last: {last_temp_1}°F)")
                    continue
                if last_temp_2 is not None and abs(current_temp_2 - last_temp_2) >= 500:
                    logging.warning(f"Temperature Sensor 2: Change exceeds limit. Skipping this reading: {current_temp_2}°F (last: {last_temp_2}°F)")
                    continue

                # Additional range check
                if not (-100 <= current_temp_1 <= 3000 and -100 <= current_temp_2 <= 3000):
                    logging.warning("Temperature out of range. Skipping this reading.")
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

            # Check if it's time to update the CSV file
            if len(data_df) % update_interval == 0:
                # Append to CSV file
                try:
                    data_df.to_csv(filename, mode='a', header=False, index=False)
                except Exception as e:
                    logging.error(f"Error writing to CSV: {e}")

            # Update plots
            update_plots(data_df)

    except KeyboardInterrupt:
        logging.info("Logging stopped by user.")
        
        # Save and show the plots
        plt.ioff()  # Turn off interactive mode
        plt.savefig(f"temperature_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")  # Save the plot
        plt.show()  # Show the final plots
        cleanup()

def update_plots(df):
    # Clear previous plots
    for ax in axs:
        ax.cla()

    # Limit number of data points to plot (last 1000 points)
    max_points = 1000
    plot_data = df.tail(max_points)

    # Check for empty DataFrame
    if plot_data.empty:
        return

    # Determine y-axis limits based on current data
    min_temp = plot_data[['Temperature Sensor 1 (°F)', 'Temperature Sensor 2 (°F)']].min().min() - 5
    max_temp = plot_data[['Temperature Sensor 1 (°F)', 'Temperature Sensor 2 (°F)']].max().max() + 5
    min_moving_avg_rate = plot_data[['Moving Average Rate of Change Sensor 1 (°F/h)', 'Moving Average Rate of Change Sensor 2 (°F/h)']].min().min() - 5
    max_moving_avg_rate = plot_data[['Moving Average Rate of Change Sensor 1 (°F/h)', 'Moving Average Rate of Change Sensor 2 (°F/h)']].max().max() + 5
    min_rate = plot_data[['Rate of Change Sensor 1 (°F/h)', 'Rate of Change Sensor 2 (°F/h)']].min().min() - 5
    max_rate = plot_data[['Rate of Change Sensor 1 (°F/h)', 'Rate of Change Sensor 2 (°F/h)']].max().max() + 5

    # Ensure limits are not NaN or Inf
    if np.isnan(min_temp) or np.isnan(max_temp) or np.isinf(min_temp) or np.isinf(max_temp):
        min_temp, max_temp = -10, 10  # Default limits
    if np.isnan(min_moving_avg_rate) or np.isnan(max_moving_avg_rate) or np.isinf(min_moving_avg_rate) or np.isinf(max_moving_avg_rate):
        min_moving_avg_rate, max_moving_avg_rate = -10, 10  # Default limits
    if np.isnan(min_rate) or np.isnan(max_rate) or np.isinf(min_rate) or np.isinf(max_rate):
        min_rate, max_rate = -10, 10  # Default limits

    # Plot configurations
    plot_configs = [
        {
            "ax": axs[0],
            "data": [plot_data['Temperature Sensor 1 (°F)'], plot_data['Temperature Sensor 2 (°F)'], plot_data['Average Temperature (°F)']],
            "labels": ['Sensor 1 (°F)', 'Sensor 2 (°F)', 'Average Temperature (°F)'],
            "title": 'Total Temperature Data from Thermocouples',
            "ylabel": 'Temperature (°F)',
            "ylim": (min_temp, max_temp)
        },
        {
            "ax": axs[1],
            "data": [plot_data['Moving Average Rate of Change Sensor 1 (°F/h)'], plot_data['Moving Average Rate of Change Sensor 2 (°F/h)']],
            "labels": ['Moving Average Rate of Change Sensor 1 (°F/h)', 'Moving Average Rate of Change Sensor 2 (°F/h)'],
            "title": 'Moving Average Rate of Change of Temperature (°F/h)',
            "ylabel": 'Rate of Change (°F/h)',
            "ylim": (min_moving_avg_rate, max_moving_avg_rate)
        },
        {
            "ax": axs[2],
            "data": [plot_data['Rate of Change Sensor 1 (°F/h)'], plot_data['Rate of Change Sensor 2 (°F/h)']],
            "labels": ['Raw Rate of Change Sensor 1 (°F/h)', 'Raw Rate of Change Sensor 2 (°F/h)'],
            "title": 'Raw Rate of Change of Temperature (°F/h)',
            "ylabel": 'Raw Rate of Change (°F/h)',
            "ylim": (min_rate, max_rate)
        },
    ]

    # Create the plots
    for config in plot_configs:
        for i, data in enumerate(config["data"]):
            config["ax"].plot(plot_data['Time'], data, label=config["labels"][i])
        config["ax"].set_title(config["title"])
        config["ax"].set_xlabel('Time')
        config["ax"].set_ylabel(config["ylabel"])
        config["ax"].set_ylim(config["ylim"])
        config["ax"].legend()
        config["ax"].grid()

    plt.draw()
    plt.pause(0.1)  # Adjust this value if needed for better performance

def cleanup():
    logging.info("Cleaning up resources.")

if __name__ == "__main__":
    log_data()
