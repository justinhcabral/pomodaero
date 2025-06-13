import cv2
import os
from datetime import datetime
import pytz

def capture_image(save_dir="~/Thesis/raspberrypi-app/data/images/snapshot", base_name="photo"):
    # Expand user directory (~) to full path
    save_dir = os.path.expanduser(save_dir)
    
    # Ensure the save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Initialize the USB camera (index 0 is typically the default USB camera)
    cap = cv2.VideoCapture(0)
    
    # Check if the camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open USB camera.")
        return False
    
    try:
        # Read a single frame
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not capture image.")
            return False
        
        # Get current time in Philippine timezone (Asia/Manila)
        ph_timezone = pytz.timezone("Asia/Manila")
        timestamp = datetime.now(ph_timezone).strftime("%Y%m%d_%H%M%S")
        
        # Generate filename with base_name and timestamp
        base_image_path = os.path.join(save_dir, f"{base_name}_{timestamp}.jpg")
        
        # Check if file exists and append counter if necessary
        counter = 1
        image_path = base_image_path
        while os.path.exists(image_path):
            image_path = os.path.join(save_dir, f"{base_name}_{timestamp}_{counter}.jpg")
            counter += 1
        
        # Save the image
        cv2.imwrite(image_path, frame)
        print(f"Image saved to: {image_path}")
        return True
        
    finally:
        # Release the camera to free resources
        cap.release()

if __name__ == "__main__":
    capture_image(base_name="photo")