Sure! Here’s your original script refactored to incorporate the suggestions mentioned earlier. The changes include better exception handling, logging, streamlined data management using a DataFrame, and improved readability.

```python
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import board
import busio
import digitalio
from adafruit_max31856 import MAX31856
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up SPI and MAX31856 sensors
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs1 = digitalio.DigitalInOut(board.D5)  # Chip select for sensor 1
cs2 = digitalio.DigitalInOut(board.D6)  # Chip select for sensor 2

sensor1 = MAX31856(spi, cs1)
sensor2 = MAX31856(spi, cs2)

# Parameters
interval = 5           # Time interval in seconds
update_interval = 60   # Time interval to update CSV in seconds

# Create a filename based on the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_data_{current_time}.csv"

# Initialize DataFrame
columns = ['Time', 'Temperature Sensor 1 (°F)', 'Rate of Change Sensor 1 (°F/s)',
           'Temperature Sensor 2 (°F)', 'Rate of Change Sensor 2 (°F/s)',
           'Average Temperature (°F)', 'Filtered Rate of Change Sensor 1 (°F/s)', 
           'Filtered Rate of Change Sensor 2 (°F/s)', 'Filtered Average Rate of Change (°F/s)']
data_df = pd.DataFrame(columns=columns)

# Setup for live plotting
plt.ion()
fig, axs = plt.subplots(4, 1, figsize=(14, 16))
plt.subplots_adjust(hspace=0.5)

def log_data():
    last_temp_1, last_temp_2 = None, None
    timestamps = []

    try:
        while True:
            current_time = time.time()
            try:
                current_temp_1 = sensor1.temperature * 9/5 + 32  # Convert to Fahrenheit
                current_temp_2 = sensor2.temperature * 9/5 + 32  # Convert to Fahrenheit
            except Exception as e:
                logging.error(f"Error reading temperatures: {e}")
                continue

            # Append data to DataFrame
            timestamps.append(current_time)
            data_df.loc[len(data_df)] = [
                pd.to_datetime(current_time, unit='s'),
                current_temp_1,
                (current_temp_1 - last_temp_1) / interval if last_temp_1 else 0,
                current_temp_2,
                (current_temp_2 - last_temp_2) / interval if last_temp_2 else 0,
                (current_temp_1 + current_temp_2) / 2,
                0,  # Placeholder for filtered rate of change
                0,  # Placeholder for filtered rate of change
                0   # Placeholder for filtered average rate of change
            ]

            last_temp_1, last_temp_2 = current_temp_1, current_temp_2
            time.sleep(interval)

            # Check if it's time to update the CSV file
            if len(data_df) % update_interval == 0:
                # Calculate filtered values
                data_df['Filtered Rate of Change Sensor 1 (°F/s)'] = data_df['Rate of Change Sensor 1 (°F/s)'].rolling(window=12).mean().fillna(0)
                data_df['Filtered Rate of Change Sensor 2 (°F/s)'] = data_df['Rate of Change Sensor 2 (°F/s)'].rolling(window=12).mean().fillna(0)
                data_df['Filtered Average Rate of Change (°F/s)'] = (data_df['Filtered Rate of Change Sensor 1 (°F/s)'] + data_df['Filtered Rate of Change Sensor 2 (°F/s)']) / 2
                
                # Append to CSV file
                data_df.to_csv(filename, mode='a', header=not bool(len(data_df)), index=False)

            # Update plots
            update_plots(data_df)

    except KeyboardInterrupt:
        logging.info("Logging stopped by user.")
        plt.ioff()  # Turn off interactive mode
        plt.show()  # Show the final plots

def update_plots(df):
    # Clear previous plots
    for ax in axs:
        ax.cla()

    # Determine y-axis limits based on current data
    min_temp = min(min(df['Temperature Sensor 1 (°F)'], default=0), min(df['Temperature Sensor 2 (°F)'], default=0)) - 5
    max_temp = max(max(df['Temperature Sensor 1 (°F)'], default=0), max(df['Temperature Sensor 2 (°F)'], default=0)) + 5
    min_rate = min(min(df['Rate of Change Sensor 1 (°F/s)'], default=0), min(df['Rate of Change Sensor 2 (°F/s)'], default=0)) - 0.5
    max_rate = max(max(df['Rate of Change Sensor 1 (°F/s)'], default=0), max(df['Rate of Change Sensor 2 (°F/s)'], default=0)) + 0.5

    # Ensure lengths match for plotting
    plot_timestamps = pd.to_datetime(df['Time'])

    # Plot configurations
    plot_configs = [
        {
            "ax": axs[0],
            "data": [df['Temperature Sensor 1 (°F)'], df['Temperature Sensor 2 (°F)']],
            "labels": ['Sensor 1 (°F)', 'Sensor 2 (°F)'],
            "title": 'Total Temperature Data from Thermocouples',
            "ylabel": 'Temperature (°F)',
            "ylim": (min_temp, max_temp)
        },
        {
            "ax": axs[1],
            "data": [df['Rate of Change Sensor 1 (°F/s)'], df['Rate of Change Sensor 2 (°F/s)']],
            "labels": ['Rate of Change Sensor 1 (°F/s)', 'Rate of Change Sensor 2 (°F/s)'],
            "title": 'Rate of Change of Temperature',
            "ylabel": 'Rate of Change (°F/s)',
            "ylim": (min_rate, max_rate)
        },
        {
            "ax": axs[2],
            "data": [df['Filtered Rate of Change Sensor 1 (°F/s)'], df['Filtered Rate of Change Sensor 2 (°F/s)']],
            "labels": ['Filtered Rate of Change Sensor 1 (°F/s)', 'Filtered Rate of Change Sensor 2 (°F/s)'],
            "title": 'Filtered Rate of Change of Temperature',
            "ylabel": 'Filtered Rate of Change (°F/s)',
            "ylim": (min_rate, max_rate)
        },
        {
            "ax": axs[3],
            "data": [df['Average Temperature (°F)']],
            "labels": ['Average Temperature (°F)'],
            "title": 'Average Temperature Over Time',
            "ylabel": 'Average Temperature (°F)',
            "ylim": (min_temp, max_temp)
        }
    ]

    # Create the plots
    for config in plot_configs:
        for i, data in enumerate(config["data"]):
            config["ax"].plot(plot_timestamps, data, label=config["labels"][i])
        config["ax"].set_title(config["title"])
        config["ax"].set_xlabel('Time')
        config["ax"].set_ylabel(config["ylabel"])
        config["ax"].set_ylim(config["ylim"])
        config["ax"].legend()
        config["ax"].grid()

    plt.draw()
    plt.pause(0.01)  # Adjust this value if needed for better performance

# Start logging data
log_data()
```

### Summary of Changes:
- **Logging**: Integrated logging to replace print statements for better traceability and debugging.
- **Data Handling**: Used a single DataFrame for all data, simplifying calculations and updates.
- **Error Handling**: Improved exception handling around critical sections.
- **Plotting Logic**: Kept the plotting logic while ensuring it operates directly on the DataFrame.

You can further customize this code based on specific needs or preferences.
