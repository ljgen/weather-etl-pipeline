from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from weather_etl import fetch_weather_data, transform_weather_data, insert_weather_data


# initialization
default_args = {
    'owner': 'tipakorn',
    'start_date': days_ago(0)
}

# Define the DAG
dag = DAG(
    'weather_data_pipeline',
    default_args=default_args,
    description='Fetch weather data and store it in MySQL',
    schedule_interval='*/30 * * * *',
    catchup=False,
    max_active_runs=1
)

# Create Airflow tasks
fetch_weather_data_task = PythonOperator(
    task_id='extract',
    python_callable=fetch_weather_data,
    dag=dag,
)

transform_weather_data_task = PythonOperator(
    task_id='transform',
    python_callable=transform_weather_data,
    dag=dag,
)

insert_weather_data_task = PythonOperator(
    task_id='load',
    python_callable=insert_weather_data,
    dag=dag,
)

# Define the task order (fetch_weather_data_task (extract) -> transform_weather_data_task (transform) -> insert_weather_data_task (load))
fetch_weather_data_task >> transform_weather_data_task >> insert_weather_data_task