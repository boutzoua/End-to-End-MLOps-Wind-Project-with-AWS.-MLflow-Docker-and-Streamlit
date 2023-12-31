from sqlalchemy import create_engine
from measurments import get_measurments
from forecast import get_forecast
from config import get_config
from pathlib import Path
import datetime
import mlflow
import pandas as pd

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

def ingest_measurments(station, past_days):
    '''Get the measurments from wind station and ingest into db. Used only for monitoring and retraining'''     
    # Get data
    df = get_measurments(station, past_days)
    # Get database url
    db_url = get_config()

    # Create an SQLAlchemy engine
    engine = create_engine(db_url)

    # Define table name based on the station
    table_name = f'measurments_{station}'

    # Query the most recent date in the measurements table
    #query = f'SELECT MAX(Time) FROM {table_name}'
    query = f'SELECT MAX("Time") as last_time FROM {table_name}'
    df_last = pd.read_sql(query, engine)
    print(f'df_last {df_last}')

    # The result will be in the first row, first column of the DataFrame
    last_date_in_db = pd.to_datetime(df_last['last_time'].iloc[0])
    if last_date_in_db is None:
        # last_date_in_db = pd.to_datetime('2010-11-26 00:00:00')
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        query = f'SELECT MAX("Time") as last_time FROM {table_name}'
        df_last = pd.read_sql(query, engine)
        last_date_in_db = pd.to_datetime(df_last['last_time'].iloc[0])

    df_new_measurements = df[df['Time'] > last_date_in_db]
    print(f' df_new_measurements \n {df_new_measurements}')
    # Check if there is new data to append
    if not df_new_measurements.empty:
        # Append new measurements to the database
        df_new_measurements.to_sql(table_name, engine, if_exists='append', index=False)
        print(f'New measurements for {station} ingested successfully into {table_name}.')
    else:
        print('No new measurements to ingest.')

def ingest_forecast():
    '''Get forecast for 3 days ahead and ingest into temp table in db. Used for inference'''
    # New forecast needs to be fed everyday because predictions for the current and next day will be made every day
    table_name = f'forecast_temp'
    
    # Get data
    df = get_forecast()

    # Get database url
    db_url = get_config()

    # Create an SQLAlchemy engine
    engine = create_engine(db_url)

    # Insert the Pandas DataFrame into the MySQL table
    try:
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f'Forecast for {df["Time"]} ingested successfully!')   
    except Exception as e:
        print(f"Data type mismatch or other data error: {e}")

def ingest_hist_forecast(past_days, forecast_days):
    '''Get past_days forecast and ingest into forecast. Used for monitoring and retraining'''
    # Get forecast past_days into
    df = get_forecast(past_days, forecast_days)

    # Get database url
    db_url = get_config()

    # Create an SQLAlchemy engine
    engine = create_engine(db_url)

    # Fetch the last date in the forecast table
    last_date_query = f'SELECT MAX("Time") as last_time FROM forecast'
    df_last = pd.read_sql(last_date_query, engine)
    last_date_in_db = pd.to_datetime(df_last['last_time'].iloc[0])
    if last_date_in_db is None:
        df.to_sql("forecast", engine, if_exists='replace', index=False)
        query = 'SELECT MAX("Time") as last_time FROM forecast'
        df_last = pd.read_sql(query, engine)
        last_date_in_db = pd.to_datetime(df_last['last_time'].iloc[0])

    df_filtered = df[df['Time'] > last_date_in_db]
        
    if not df_filtered.empty:
        table_name = 'forecast'
        df_filtered.to_sql(table_name, engine, if_exists='append', index=False)
        print(f"Appended new forecast data from {last_date_in_db + datetime.timedelta(days=1)} to {datetime.date.today()} to the main table.")
    else:
        print("No new dates to append to the forecast table.")

def ingest_predictions_temp(station, pred):
    '''Used for inference. Ingest predictions of the model to the RDS postgres.'''
    table_name = f'current_pred_{station}'
    
    # Get database url
    db_url = get_config()

    # Create an SQLAlchemy engine
    engine = create_engine(db_url)

    pred.to_sql(table_name, engine, if_exists='replace', index=False)
    print(f'Prediction for {station} ingested successfully!')

def record_training(station, model_name):
    '''Records the last retraining of the model to the RDS postgres'''
    table_name = f'table_update_{station}'

    db_url = get_config()

    # Create an SQLAlchemy engine
    engine = create_engine(db_url)

    # Create a DataFrame with the necessary data
    df = pd.DataFrame({
        'model_name': [model_name],
        'retrained_date': [datetime.datetime.now().date()]  # Gets today's date
    })

    # Append the data to the SQL table
    df.to_sql(table_name, engine, if_exists='append', index=False)

def ingest_mlflow(experiment_id):
    db_url = get_config()
    print(db_url)
    # Create an SQLAlchemy engine
    engine = create_engine(db_url)
    experiment_data = mlflow.search_runs(experiment_ids=experiment_id)
    print(experiment_data)
    # experiment_data.to_sql("runs", engine, if_exists='replace', index=False)

if __name__ == '__main__': 
    # ingest_measurments('rewa',3)
    # ingest_hist_forecast(1,4)
    # ingest_forecast()
    ingest_mlflow(experiment_id ="123121000883176933")