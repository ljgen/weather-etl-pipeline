import logging
import sys
import requests
import os
import pytz
import mysql.connector
from datetime import datetime


def fetch_weather_data(ti):
    try:
        user_api = os.getenv('USER_API_WEATHER')
        city_name = 'Bangkok'
        weather_api_link = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={user_api}"
        weather_api = requests.get(weather_api_link)
        api_data = weather_api.json()

        if api_data['cod'] == 200:

            # Push api_data to XCom
            ti.xcom_push(key="weather_data", value=api_data)

            logging.info("Fetch weather data successfully!")

        else:
            raise ValueError("Could not retrieve weather data from the API. Response code: %s", api_data.get('cod'))

    except Exception as e:
       logging.error(f"Error fetching weather data: {e}")
       sys.exit(1)


def transform_weather_data(ti):
    # Pull api_data from XCom
    api_data = ti.xcom_pull(task_ids='extract', key='weather_data')

    try:
        weather_data = {
            "temperature": round((api_data['main']['temp']) -273.15, 2),
            "weather": f"{api_data['weather'][0]['main']} - {api_data['weather'][0]['description']}",
            "pressure": api_data['main']['pressure'],
            "humidity": api_data['main']['humidity'],
            "temp_min": round((api_data['main']['temp_min']) -273.15, 2),
            "temp_max": round((api_data['main']['temp_max']) -273.15, 2),
            "wind_speed": api_data['wind']['speed'],
            "clouds": api_data['clouds']['all'],
            "date_time": datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%Y-%m-%d %H:%M:%S")
        }
        logging.info(f"Weather data: {weather_data}")

        # Push weather_data to XCom
        ti.xcom_push(key="weather_data", value=weather_data)

    except Exception as e:
       logging.error(f"Error transform weather data: {e}")
       sys.exit(1)       


def create_table(conn):
    table_query = """
        CREATE TABLE IF NOT EXISTS weather (
            id INT AUTO_INCREMENT PRIMARY KEY,
            temperature FLOAT NOT NULL,
            weather VARCHAR(50) NOT NULL,
            pressure INT NOT NULL,
            humidity INT NOT NULL,
            temp_min FLOAT NOT NULL,
            temp_max FLOAT NOT NULL,
            wind_speed FLOAT NOT NULL,
            clouds INT NOT NULL,
            date_time DATETIME NOT NULL
        );
        """
    try:
        with conn.cursor() as cursor:
            logging.info(f"Creating table using connection: {conn.is_connected()}")
            cursor.execute(table_query)
            conn.commit()
            cursor.close()
            
            logging.info("Table created successfully!")

    except mysql.connector.Error as err:
        logging.error(f"MySQL Error while creating table: {err}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while creating table: {e}")
        raise


def insert_data(conn, data):
    insert_query = """
        INSERT INTO weather (
            temperature, weather, pressure, humidity, temp_min, temp_max, wind_speed, clouds, date_time
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """
    try:
        with conn.cursor() as cursor:

            # Validate required fields
            if not all(['temperature', 'weather', 'pressure', 'humidity', 'temp_min', 'temp_max', 'wind_speed', 'clouds', 'date_time']):
                raise ValueError("Missing required fields in the data")
        
            # Extract values and execute the query
            values = (
                data['temperature'], data['weather'], data['pressure'],
                data['humidity'], data['temp_min'], data['temp_max'],            
                data['wind_speed'], data['clouds'], data['date_time'] 
            )

            cursor.execute(insert_query, values)
            conn.commit()
            cursor.close()

            logging.info("Data inserted successfully!")

    except mysql.connector.Error as err:
        logging.error(f"MySQL Error while inserting data: {err}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while inserting data: {e}")
        raise


def mysql_connection():
    try:
        connection = mysql.connector.connect(
            host='mysql',
            user='db_mysql',
            password='db_mysql',
            database='weather_api'
            )

        logging.info("Connected to MySQL")

        return connection

    except mysql.connector.Error as err:
        logging.error(f"MySQL connection error: {err}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


def insert_weather_data(ti):
    # Pull weather_data from XCom
    weather_data = ti.xcom_pull(task_ids='transform', key='weather_data')

    db_conn = mysql_connection()

    try:
        # create_database(mysql_conn)
        create_table(db_conn)
        insert_data(db_conn, weather_data)
    
    except Exception as e:
        logging.error(f"Error inserting weather data into database: {e}")
        sys.exit(1)
    finally:
        if db_conn.is_connected():
            db_conn.close()
            logging.info("MySQL connection closed.")