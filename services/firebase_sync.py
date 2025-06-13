import time
import requests
import json
import os
import glob
import subprocess
import sys
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

# Image directory path
IMAGE_DIR = "/home/cabs/Thesis/raspberrypi-app/data/images/snapshot"

# Detection script path - AUTO-DETECT THE CORRECT PATH
def find_detection_script():
    """
    Automatically find the detect_tomatoes.py script in common locations.
    
    Returns:
        str: Path to detect_tomatoes.py, or None if not found
    """
    possible_paths = [
        "/home/cabs/Thesis/raspberrypi-app/detect_tomatoes.py",
        "/home/cabs/Thesis/raspberrypi-app/services/detect_tomatoes.py", 
        "/home/cabs/detect_tomatoes.py",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "detect_tomatoes.py"),
        # Add the current directory where this script is running
        "./detect_tomatoes.py"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found detection script at: {path}")
            return path
    
    print("ERROR: detect_tomatoes.py not found in any expected location!")
    print("Searched in:")
    for path in possible_paths:
        print(f"  - {path}")
    return None

def run_growth_stage_detection():
    """
    Runs the tomato detection script and extracts the growth stage.
    
    Returns:
        int: Growth stage (1, 2, or 3), or None if detection failed
    """
    try:
        print("Running growth stage detection...")
        
        # Find the detection script
        detection_script_path = find_detection_script()
        if not detection_script_path:
            print("Cannot proceed without detection script")
            return None
        
        # Check if there are any images to process
        if not os.path.exists(IMAGE_DIR):
            print(f"Image directory does not exist: {IMAGE_DIR}")
            return None
            
        # Check if there are any images in the directory
        image_files = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        if not image_files:
            print(f"No images found in {IMAGE_DIR}")
            return None
        
        print(f"Found {len(image_files)} image(s) in snapshot directory")
        
        # Run the detection script
        cmd = [sys.executable, detection_script_path, "--model-type", "pytorch"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        print(f"Detection script return code: {result.returncode}")
        
        if result.returncode == 0:
            output_lines = result.stdout.split('\n')
            growth_stage = None
            detection_found = False
            
            # Look for the growth stage in the output
            for line in output_lines:
                print(f"Detection output: {line}")  # Print all output for debugging
                
                # Check if any objects were detected
                if "Detected" in line and "object(s)" in line:
                    detection_found = True
                
                if line.startswith("Growth Stage:"):
                    try:
                        stage_str = line.split(":")[1].strip()
                        if stage_str.isdigit():
                            growth_stage = int(stage_str)
                            print(f"Successfully detected growth stage: {growth_stage}")
                        elif stage_str == "Unknown":
                            print("Growth stage detection: Unknown (objects detected but stage unclear)")
                            growth_stage = None
                    except (IndexError, ValueError) as e:
                        print(f"Error parsing growth stage: {e}")
            
            if not detection_found:
                print("No objects detected in the image")
            
            return growth_stage
        else:
            print(f"Detection script failed with return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Detection script timed out (>5 minutes)")
        return None
    except Exception as e:
        print(f"Error running detection script: {e}")
        return None

def get_latest_image():
    """
    Gets the latest captured image from the image directory.
    
    Returns:
        str: Path to the latest image file, or None if no images found
    """
    try:
        # Search for common image formats
        image_patterns = [
            os.path.join(IMAGE_DIR, "*.jpg"),
        ]
        
        all_images = []
        for pattern in image_patterns:
            all_images.extend(glob.glob(pattern))
        
        if not all_images:
            print("No images found in the directory")
            return None
        
        # Get the most recently created image
        latest_image = max(all_images, key=os.path.getctime)
        print(f"Latest image found: {latest_image}")
        return latest_image
        
    except Exception as e:
        print(f"Error finding latest image: {e}")
        return None

def delete_image_file(image_path):
    """
    Deletes the specified image file from the local filesystem.
    
    Args:
        image_path (str): Path to the image file to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Image deleted successfully: {os.path.basename(image_path)}")
            return True
        else:
            print(f"Image file not found for deletion: {image_path}")
            return False
    except Exception as e:
        print(f"Error deleting image file: {e}")
        return False

def get_firebase_auth_token():
    """
    Get Firebase Auth token using Anonymous Authentication.
    
    Returns:
        str: ID token for authenticated requests, or None if authentication fails
    """
    try:
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp"
        params = {"key": FIREBASE_CONFIG["apiKey"]}
        data = {"returnSecureToken": True}
        
        response = requests.post(auth_url, params=params, json=data)
        
        if response.status_code == 200:
            auth_data = response.json()
            return auth_data.get('idToken')
        else:
            print(f"Error getting auth token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None

def upload_image_to_firebase_storage(image_path, email, date_string):
    """
    Uploads an image to Firebase Storage and returns the download URL.
    
    Args:
        image_path (str): Local path to the image file
        email (str): User email for folder structure
        date_string (str): Date string for folder structure
        
    Returns:
        str: Download URL of the uploaded image, or None if upload failed
    """
    try:
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return None
        
        # Get file extension
        file_extension = os.path.splitext(image_path)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.bmp']:
            print(f"Unsupported image format: {file_extension}")
            return None
        
        # Get authentication token
        auth_token = get_firebase_auth_token()
        if not auth_token:
            print("Failed to get authentication token")
            return None
        
        # Create storage path: email/date/timestamp_image.ext
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_image{file_extension}"
        storage_path = f"{email}/{date_string}/{filename}"
        
        # Read image file
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        # Firebase Storage upload URL
        bucket_name = FIREBASE_CONFIG["storageBucket"]
        upload_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o"
        
        # Set content type based on file extension
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp'
        }
        content_type = content_type_map.get(file_extension, 'image/jpeg')
        
        # Upload parameters with authentication
        params = {
            "name": storage_path
        }
        
        headers = {
            "Content-Type": content_type,
            "Authorization": f"Bearer {auth_token}"
        }
        
        # Upload the image
        response = requests.post(upload_url, params=params, headers=headers, data=image_data)
        
        if response.status_code == 200:
            # Get download URL
            download_token = response.json().get('downloadTokens')
            download_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{storage_path.replace('/', '%2F')}?alt=media&token={download_token}"
            print(f"Image uploaded successfully: {filename}")
            return download_url
        else:
            print(f"Error uploading image: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error uploading image to Firebase Storage: {e}")
        return None

def save_environmental_data_to_firebase(email, data):
    """
    Saves pH, EC, temperature, humidity data, growth stage, and image URL to Firebase Firestore using REST API.
    
    Args:
        email (str): User email
        data (dict): Dictionary containing pH, EC, temperature, humidity, growth_stage, and imageUrl values
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
                "timestamp": {"timestampValue": ph_time.isoformat()}
            }
        }
        
        # Add growth stage
        if data.get('growth_stage') is not None:
            firebase_data["fields"]["growthStage"] = {"integerValue": str(data['growth_stage'])}
            print(f"Growth stage will be saved as: {data['growth_stage']}")
        else:
            firebase_data["fields"]["growthStage"] = {"nullValue": None}
            print("No growth stage detected, saving as null")
        
        # Add temperature and humidity if available
        if data['temperature'] is not None:
            firebase_data["fields"]["temperature"] = {"doubleValue": round(data['temperature'], 2)}
        else:
            firebase_data["fields"]["temperature"] = {"nullValue": None}
            
        if data['humidity'] is not None:
            firebase_data["fields"]["humidity"] = {"doubleValue": round(data['humidity'], 2)}
        else:
            firebase_data["fields"]["humidity"] = {"nullValue": None}
        
        # Add image URL if available
        if data.get('imageUrl'):
            firebase_data["fields"]["imageUrl"] = {"stringValue": data['imageUrl']}
        else:
            firebase_data["fields"]["imageUrl"] = {"nullValue": None}
        
        # Construct the Firestore REST API URL
        project_id = FIREBASE_CONFIG["projectId"]
        collection_path = f"users/{email}/environmentalHistory/{date_string}"
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_path}"
        
        # Add API key to the request
        params = {"key": FIREBASE_CONFIG["apiKey"]}
        
        # Make the request
        response = requests.patch(url, json=firebase_data, params=params)
        
        if response.status_code == 200:
            print(f"\n=== Firebase Upload Success ===")
            print(f"Environmental data saved for {email} on {date_string}")
            print(f"   pH: {round(data['ph'], 2)}, EC: {round(data['ec'], 2)} mS/cm")
            if data['temperature'] is not None and data['humidity'] is not None:
                print(f"   Temperature: {round(data['temperature'], 2)}°C, Humidity: {round(data['humidity'], 2)}%")
            else:
                print("   Temperature/Humidity: Failed to read DHT11")
            if data.get('growth_stage') is not None:
                print(f"   Growth Stage: {data['growth_stage']}")
            else:
                print("   Growth Stage: Not detected")
            if data.get('imageUrl'):
                print(f"   Image uploaded and URL saved")
            else:
                print("   No image uploaded")
            print("===============================\n")
        else:
            print(f"Error saving to Firebase: {response.status_code}")
            print(f"   Response: {response.text}")
        
    except Exception as error:
        print(f"Error saving environmental data: {error}")

def main():
    """
    Main function to read sensors, run detection, upload image, and send data to Firebase.
    """
    try:
        print("=== Starting Sensor Data Collection and Upload ===\n")
        
        # Get current date for folder structure
        ph_tz = pytz.timezone('Asia/Manila')
        current_date = datetime.now(ph_tz).strftime("%Y-%m-%d")
        user_email = "ivanilla.ivanilla@gmail.com"
        
        # Get sensor data from sensors.py
        print("Reading sensors...")
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
        
        # Run growth stage detection
        print("\n" + "="*50)
        growth_stage = run_growth_stage_detection()
        print("="*50 + "\n")
        
        # Get and upload the latest image from snapshot directory only
        print("Processing image upload...")
        
        # Only use original snapshot images for Firebase upload
        latest_image_path = get_latest_image()
        if latest_image_path:
            print(f"Using snapshot image: {os.path.basename(latest_image_path)}")
        else:
            print("No snapshot image found for upload")
        
        image_url = None
        if latest_image_path:
            image_url = upload_image_to_firebase_storage(latest_image_path, user_email, current_date)
            
            # Delete the local image file after successful upload
            if image_url:  # Only delete if upload was successful
                delete_image_file(latest_image_path)
            else:
                print("Image upload failed, keeping local file")
        
        # Combine data for Firebase
        sensor_data = {
            'ph': ph_data['ph'],
            'ec': tds_data['ec'],
            'temperature': dht_data['temperature'],
            'humidity': dht_data['humidity'],
            'growth_stage': growth_stage,
            'imageUrl': image_url
        }
        
        # Send to Firebase
        save_environmental_data_to_firebase(user_email, sensor_data)
        
    except Exception as e:
        print(f"Error in main process: {e}")

if __name__ == "__main__":
    main()