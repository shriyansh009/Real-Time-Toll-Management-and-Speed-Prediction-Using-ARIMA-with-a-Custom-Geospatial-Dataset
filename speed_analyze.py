import pandas as pd
import numpy as np
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import geopandas as gpd
from shapely.geometry import Point
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_squared_error, r2_score 
from scipy.signal import savgol_filter
import plotly.graph_objs as go
import plotly.io as pio




def speed_png(file, smoothing_window=5, poly_order=2, interactive=False):
    # Load and clean data
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    data_clean = df.dropna(subset=['timestamp', 'latitude', 'longitude'])

    # Function to convert MM:SS format to seconds
    def convert_to_seconds(time_str):
        minutes, seconds = time_str.split(':')
        return int(minutes) * 60 + float(seconds)

    data_clean['timestamp'] = data_clean['timestamp'].apply(convert_to_seconds)

    # Function to calculate distance between two lat/lon points
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Radius of the Earth in km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    # Calculate speed
    data_clean = data_clean.sort_values(by='timestamp')
    data_clean['time_diff'] = data_clean['timestamp'].diff().shift(-1)
    data_clean['distance'] = haversine(data_clean['latitude'], data_clean['longitude'],
                                       data_clean['latitude'].shift(-1), data_clean['longitude'].shift(-1))
    data_clean['speed'] = data_clean['distance'] / (data_clean['time_diff'] / 3600)  # speed in km/h

    # Drop rows where speed is NaN, inf, or -inf
    data_clean = data_clean.dropna(subset=['speed'])
    data_clean = data_clean[np.isfinite(data_clean['speed'])]

    # Features and target variable
    X = data_clean[['latitude', 'longitude']]
    y = data_clean['speed']

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train the model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predict speeds
    data_clean['predicted_speed'] = model.predict(X)

    # Smooth the actual speed data using Savitzky-Golay filter
    data_clean['smoothed_speed'] = savgol_filter(data_clean['speed'], smoothing_window, poly_order)

    # Calculate error metrics
    mse = mean_squared_error(y, data_clean['predicted_speed'])
    r2 = r2_score(y, data_clean['predicted_speed'])
    print(f'Mean Squared Error: {mse:.2f}')
    print(f'R-squared: {r2:.2f}')

    # Convert timestamp to minutes for plotting
    data_clean['timestamp_minutes'] = data_clean['timestamp'] / 60

    if interactive:
        # Create an interactive plot with Plotly
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=data_clean['timestamp_minutes'], y=data_clean['speed'],
                                 mode='lines', name='Actual Speed', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=data_clean['timestamp_minutes'], y=data_clean['smoothed_speed'],
                                 mode='lines', name='Smoothed Speed', line=dict(color='orange', dash='dot')))
        fig.add_trace(go.Scatter(x=data_clean['timestamp_minutes'], y=data_clean['predicted_speed'],
                                 mode='lines', name='Predicted Speed', line=dict(color='blue')))

        fig.update_layout(title='Speed Over Time', xaxis_title='Timestamp (minutes)',
                          yaxis_title='Speed (km/h)', legend_title='Legend')

        pio.show(fig)
        return None

    # Create a static plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot actual speed
    ax.plot(data_clean['timestamp_minutes'], data_clean['speed'], 
            label='Actual Speed', color='red', linewidth=1, linestyle='-')

    # Plot smoothed speed
    ax.plot(data_clean['timestamp_minutes'], data_clean['smoothed_speed'], 
            label='Smoothed Speed', color='orange', linewidth=1.5, linestyle='--')

    # Plot predicted speed
    ax.plot(data_clean['timestamp_minutes'], data_clean['predicted_speed'], 
            label='Predicted Speed', color='blue', linewidth=2, linestyle='-')

    # Set labels
    ax.set_xlabel('Timestamp (minutes)')
    ax.set_ylabel('Speed (km/h)')

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}')) 
    ax.yaxis.set_major_locator(plt.MaxNLocator(10)) 
    ax.grid(True)

    ax.legend()

    # Save the plot to a PNG image in memory
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
    buf.seek(0)
    plt.close()

    # Encoding the image data to base64 to embed it into an HTML file
    image_data = base64.b64encode(buf.read()).decode('utf-8')
    return image_data



def lat_long(file):
    df = pd.read_csv(file)
    data_clean = df.dropna(subset=['latitude', 'longitude'])
     
    # Extract latitude and longitude values
    latitudes = data_clean['latitude']
    longitudes = data_clean['longitude']

    # Create a scatter plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(longitudes, latitudes, c='blue', marker='o')
    ax.set_title('Latitude and Longitude Plot')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.grid(True)

    # Creating buffer for image data
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=300)
    buf.seek(0)
    plt.close()        
    # Encoding the image data to base64 to emmbeded it into html file
    image_data = base64.b64encode(buf.read()).decode('utf-8') 
    return image_data





def arima_analysis(file, train_ratio=0.6, arima_order=(1, 1, 1), seasonal=False, seasonal_order=(1, 1, 1, 12)):
    # Load data
    data = pd.read_csv(file)
    target_speed = data['speed']

    # Check stationarity
    adf_test = adfuller(target_speed)
    print(f"ADF Statistic: {adf_test[0]}")
    print(f"p-value: {adf_test[1]}")
    if adf_test[1] > 0.05:
        print("Warning: The data is non-stationary. Consider differencing or transformation.")

    # Split data
    train_size = int(len(target_speed) * train_ratio)
    train, test = target_speed[:train_size], target_speed[train_size:]

    # ACF and PACF plots
    fig, ax = plt.subplots(2, 1, figsize=(12, 8))
    plot_acf(train, ax=ax[0], lags=40, title='ACF - Autocorrelation Function')
    plot_pacf(train, ax=ax[1], lags=40, title='PACF - Partial Autocorrelation Function')
    plt.tight_layout()
    plt.show()

    # ARIMA model
    if seasonal:
        model = ARIMA(train, order=arima_order, seasonal_order=seasonal_order)
    else:
        model = ARIMA(train, order=arima_order)
    
    model_fit = model.fit()

    # Model diagnostics
    print(model_fit.summary())

    # Residual diagnostics
    residuals = model_fit.resid
    fig, ax = plt.subplots(2, 1, figsize=(12, 8))
    ax[0].plot(residuals, label='Residuals')
    ax[0].set_title('Residuals of the ARIMA Model')
    ax[0].legend()
    plot_acf(residuals, ax=ax[1], lags=40)
    plt.tight_layout()
    plt.show()

    # Forecast
    forecast_steps = len(test)
    forecast = model_fit.forecast(steps=forecast_steps)
    forecast_ci = model_fit.get_forecast(steps=forecast_steps).conf_int()

    # Create a plot for the forecast
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(train.index, train, label='Train', color='blue')
    ax.plot(test.index, test, label='Test', color='orange')
    ax.plot(test.index, forecast, label='Forecast', color='green', linestyle='--')
    ax.fill_between(test.index, forecast_ci.iloc[:, 0], forecast_ci.iloc[:, 1], color='gray', alpha=0.3, label='95% CI')
    ax.set_title('ARIMA Model - Target Speed Forecast')
    ax.set_xlabel('Time (Index)')
    ax.set_ylabel('Target Speed')
    ax.legend()
    ax.grid(True)

    # Save the plot to a PNG image in memory
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
    buf.seek(0)
    plt.close()

    # Encoding the image data to base64 to embed it into an HTML file
    image_data = base64.b64encode(buf.read()).decode('utf-8') 

    return image_data








def scatter_plot(file, interactive=False, detect_outliers=False, map_overlay=False, map_shapefile=None):
    # Load data
    data = pd.read_csv(file)

    # Optional: Outlier detection
    if detect_outliers:
        isolation_forest = IsolationForest(contamination=0.05)
        data['anomaly'] = isolation_forest.fit_predict(data[['longitude', 'latitude', 'speed']])
        data = data[data['anomaly'] == 1]

    # Convert to GeoDataFrame for mapping
    if map_overlay:
        geometry = [Point(xy) for xy in zip(data['longitude'], data['latitude'])]
        geo_df = gpd.GeoDataFrame(data, geometry=geometry)

    # Plotting
    plt.figure(figsize=(12, 10))
    
    if map_overlay and map_shapefile:
        map_df = gpd.read_file(map_shapefile)
        base = map_df.plot(color='white', edgecolor='black')
        geo_df.plot(ax=base, marker='o', c=geo_df['speed'], cmap='viridis', markersize=50, alpha=0.6)
    else:
        sns.scatterplot(data=data, x='longitude', y='latitude', hue='speed', palette='viridis', s=100, edgecolor='none')

    plt.title('Geospatial Visualization of Speed')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend(title='Speed', loc='upper right')
    plt.grid(True)

   
    # Save the plot to a PNG image in memory
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
    buf.seek(0)
    plt.close()

    # Encoding the image data to base64 to embed it into an HTML file
    image_data = base64.b64encode(buf.read()).decode('utf-8')

    return image_data





def analyze_data():
    # Load the CSV file
    data = pd.read_csv('datasets/simulation.csv')

    # Group by Vehicle
    grouped_by_vehicle = data.groupby('Vehicle').agg({
        'Total': 'mean',
        'distance': 'mean',
        'tax': 'mean'
    }).reset_index()

    # Group by Destinaton1 and Destination2
    grouped_by_destination = data.groupby(['Destinaton1', 'Destination2']).agg({
        'Total': 'mean',
        'distance': 'mean',
        'tax': 'mean'
    }).reset_index()

    # Aggregate by User_id
    aggregated_by_user = data.groupby('user_id').agg({
        'Total': 'sum',
        'distance': 'sum'
    }).reset_index()

    # Detect outliers using the IQR method
    def detect_outliers(df, column):
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return df[(df[column] < lower_bound) | (df[column] > upper_bound)]

    outliers_fine = detect_outliers(data, 'Fine')
    outliers_total = detect_outliers(data, 'Total')
    outliers_distance = detect_outliers(data, 'distance')
    outliers_tax = detect_outliers(data, 'tax')

    return {
        "grouped_by_vehicle": grouped_by_vehicle,
        "grouped_by_destination": grouped_by_destination,
        "aggregated_by_user": aggregated_by_user,
        "outliers": {
            'Fine': outliers_fine,
            'Total': outliers_total,
            'distance': outliers_distance,
            'tax': outliers_tax
        }
    }