import time
import os
import automationhat
import Adafruit_DHT
from influxdb import InfluxDBClient
from balena import Balena

class PlantSaver:

    def __init__(self):

        # Variables
        self.dht_sensor = Adafruit_DHT.DHT22
        self.dht_pin = int(self.set_variable("dht_pin", 8))
        self.max_value = float(self.set_variable("max_value", 2.77)) 
        self.min_value = float(self.set_variable("min_value", 1.46)) 
        self.target_soil_moisture = 50 
        self.target_soil_threshold = 10 

        # Initial status
        self.status = 'Starting'
        self.status_code = 0
        self.moisture_level = None
        self.pumping = False
        self.temperature = 0
        self.humidity = 0

        # TODO only create the database if it doesn't already exist
        self.influx_client = InfluxDBClient(self.influx_db_host, 8086, database=self.influx_db_name)
        self.influx_client.create_database(self.influx_db_name)

    # Checks if there is an environment variable set, otherwise save the default value
    def set_variable(self, name, default_value):
        if name in os.environ:
            self.value = os.environ.get(name)
        else: 
            self.value = default_value
        return self.value

    def read_moisture(self):
        self.moisture_level= 100-(automationhat.analog.one.read()-self.min_value)/((self.max_value-self.min_value)/100)

    def read_temperature_humidity(self):
        self.humidity, self.temperature = Adafruit_DHT.read_retry(self.dht_sensor, self.dht_pin)
    
    def update_sensors(self):
        self.read_moisture()
        self.read_temperature_humidity()
        # self.read_float_switch()
    
   # Generate a status string so we have something to show in the logs
    # We also generate a status code which is used in the front end UI
    def update_status(self):
        if self.moisture_level < self.target_soil_moisture-self.target_soil_threshold:
            status = 'Too dry'
            self.status_code = 1
        elif self.moisture_level > self.target_soil_moisture+self.target_soil_threshold:
            status = 'Too wet'
            self.status_code = 2
        else:
            status = 'OK'
            self.status_code = 3

    # Store the current instance measurements within InfluxDB
    def write_measurements(self):
        measurements = [
            {
                'measurement': 'plant-data',
                'fields': {
                    'moisture': float(self.moisture_level),
                    'pumping': int(self.pumping),
                    # 'water_left': int(self.water_left),
                    'status': int(self.status_code),
                    'temperature': float(self.temperature),
                    'humidity': float(self.humidity)
                }
            }
        ]

        self.influx_client.write_points(measurements)

    # Generate a status string so we have something to show in the logs
    # We also generate a status code which is used in the front end UI
    def update_status(self):
        if self.moisture_level < self.target_soil_moisture-self.target_soil_threshold:
            status = 'Too dry'
            self.status_code = 1
        elif self.moisture_level > self.target_soil_moisture+self.target_soil_threshold:
            status = 'Too wet'
            self.status_code = 2
        else:
            status = 'OK'
            self.status_code = 3

        if self.pumping == True:
            status = status + ', pump running'

        if self.water_left == False:
            status = status + ', water low'

        self.status = status

    # Refresh the relevant things - designed to be run once every 10 seconds
    def tick(self):
        self.update_sensors()
        self.update_status()
        self.write_measurements()