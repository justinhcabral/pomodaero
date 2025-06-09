#!/usr/bin/python3
import time
import requests
import json
from datetime import datetime
import pytz
from sensors import read_tds, read_ph, read_dht11  # Import functions from sensors.py

# Firebase configuration (using your project details)
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDv6v4JDHyYnBjEu6d1IJCH9aaIG3597SM",
    "authDomain": "pomodaero-91bd3.firebaseapp.com",
    "projectId": "pomodaero-91bd3",
    "storageBucket": "pomodaero-91bd3.firebasestorage.app",
    "messagingSenderId": "679579545364",
    "appId": "1:679579545364:web:e485100c74448bb46a9c01",
    "measurementId": "G-7RMP6QB4C0",
}

def save_environmental_data_to_firebase(email, data):
    """
    Saves pH, EC, temperature, and humidity data to Firebase Firestore using REST API.
    
    Args:
        email (str): User email
        data (dict): Dictionary containing pH, EC, temperature, and humidity values
    """
    try:
        # Get current date string in Philippines time
        ph_tz = pytz.timezone('Asia/Manila')
        ph_time = datetime.now(ph_tz)
        date_string = ph_time.strftime("%Y-%m-%d")
        
        # Prepare the data for Firebase
        firebase_data = {
            "fields": {
                "pH": {"doubleValue": round(data['ph'], 2)},
                "EC": {"doubleValue": round(data['ec'], 2)},
                "timestamp": {"timestampValue": ph_time.isoformat()},
                "growthStage": {"integerValue": "2"},
                "imageUrl": {"nullValue": None}
            }
        }
        
        # Add temperature and humidity if available
        if data['temperature'] is not None:
            firebase_data["fields"]["temperature"] = {"doubleValue": round(data['temperature'], 2)}
        else:
            firebase_data["fields"]["temperature"] = {"nullValue": None}
            
        if data['humidity'] is not None:
            firebase_data["fields"]["humidity"] = {"doubleValue": round(data['humidity'], 2)}
        else:
            firebase_data["fields"]["humidity"] = {"nullValue": None}
        
        # Construct the Firestore REST API URL
        project_id = FIREBASE_CONFIG["projectId"]
        collection_path = f"users/{email}/environmentalHistory/{date_string}"
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_path}"
        
        # Add API key to the request
        params = {"key": FIREBASE_CONFIG["apiKey"]}
        
        # Make the request
        response = requests.patch(url, json=firebase_data, params=params)
        
        if response.status_code == 200:
            print(f"Environmental data saved for {email} on {date_string}")
            print(f"   pH: {round(data['ph'], 2)}, EC: {round(data['ec'], 2)} mS/cm")
            if data['temperature'] is not None and data['humidity'] is not None:
                print(f"   Temperature: {round(data['temperature'], 2)}°C, Humidity: {round(data['humidity'], 2)}%")
            else:
                print("   Temperature/Humidity: Failed to read DHT11")
        else:
            print(f"Error saving to Firebase: {response.status_code}")
            print(f"   Response: {response.text}")
        
    except Exception as error:
        print(f"Error saving environmental data: {error}")

def main():
    """
    Main function to read sensors and send data to Firebase.
    """
    try:
        # Get sensor data from sensors.py
        tds_data = read_tds()
        time.sleep(0.1)  # Delay between channel readings
        ph_data = read_ph()
        dht_data = read_dht11()
        
        # Print local readings
        print(f"TDS Voltage: {tds_data['voltage']:.3f} V, TDS: {tds_data['tds']:.2f} ppm, EC: {tds_data['ec']:.2f} mS/cm")
        print(f"pH Voltage: {ph_data['voltage']:.3f} V, pH: {ph_data['ph']:.2f}")
        if dht_data['temperature'] is not None and dht_data['humidity'] is not None:
            print(f"Temperature: {dht_data['temperature']:.2f} °C, Humidity: {dht_data['humidity']:.2f} %")
        else:
            print("DHT11 reading failed")
        
        # Combine data for Firebase
        sensor_data = {
            'ph': ph_data['ph'],
            'ec': tds_data['ec'],
            'temperature': dht_data['temperature'],
            'humidity': dht_data['humidity']
        }
        
        # Send to Firebase
        user_email = "ivanilla.ivanilla@gmail.com"  # Replace with your user email
        save_environmental_data_to_firebase(user_email, sensor_data)
        
    except Exception as e:
        print(f"Error reading sensors or sending to Firebase: {e}")

if __name__ == "__main__":
    main()