## NEW CODE

import argparse
import cv2
import numpy as np
from ultralytics import YOLO
import onnxruntime as ort
import os
import glob
from datetime import datetime

# Hardcoded image directory path
IMAGE_DIR = "/home/cabs/Thesis/raspberrypi-app/data/images/snapshot"

def get_most_recent_image(directory):
    """Get the most recent image file from the directory."""
    # Common image extensions
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']
    
    image_files = []
    for extension in image_extensions:
        image_files.extend(glob.glob(os.path.join(directory, extension)))
        image_files.extend(glob.glob(os.path.join(directory, extension.upper())))
    
    if not image_files:
        return None
    
    # Get the most recent file based on modification time
    most_recent = max(image_files, key=os.path.getmtime)
    return most_recent

def run_pytorch_model(model_path, image_path, img_size=320):
    """Run inference with YOLOv11 PyTorch model (.pt) on an image."""
    try:
        # If image_path is a directory, get the most recent image
        if os.path.isdir(image_path):
            image_path = get_most_recent_image(image_path)
            if image_path is None:
                print(f"Error: No image files found in directory")
                return
            print(f"Processing most recent image: {os.path.basename(image_path)}")
        
        if not os.path.exists(image_path):
            print(f"Error: Image file {image_path} not found")
            return
        
        if not os.path.exists(model_path):
            print(f"Error: Model file {model_path} not found")
            return
        
        model = YOLO(model_path)
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "/home/cabs/Thesis/raspberrypi-app/data/images/annotated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get original filename without extension
        original_name = os.path.splitext(os.path.basename(image_path))[0]
        output_filename = f"{original_name}_annotated_{timestamp}.jpg"
        output_path = os.path.join(output_dir, output_filename)
        
        # Run inference without default saving
        results = model.predict(source=image_path, imgsz=img_size, conf=0.25, save=False)
        
        # Get annotated image
        annotated_img = results[0].plot()
        
        # Save the image
        success = cv2.imwrite(output_path, annotated_img)
        if success:
            print(f"Result successfully saved to {output_path}")
            
            # Print detection results
            detections = results[0]
            if len(detections.boxes) > 0:
                print(f"Detected {len(detections.boxes)} object(s):")
                
                # Track detected stages for growth stage determination
                detected_stages = set()
                
                for i, box in enumerate(detections.boxes):
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = model.names.get(cls, f"Class_{cls}")
                    print(f"  {i+1}. {class_name}: {conf:.2f} confidence")
                    
                    # Extract stage number from class name
                    if "Stage 1" in class_name:
                        detected_stages.add(1)
                    elif "Stage 2" in class_name:
                        detected_stages.add(2)
                    elif "Stage 3" in class_name:
                        detected_stages.add(3)
                
                # Determine overall growth stage (highest stage detected)
                if detected_stages:
                    growth_stage = max(detected_stages)
                    print(f"\nGrowth Stage: {growth_stage}")
                else:
                    print("\nGrowth Stage: Unknown")
            else:
                print("No objects detected")
        else:
            print(f"Error: Failed to save image to {output_path}")
            
    except Exception as e:
        print(f"Error in PyTorch inference: {str(e)}")

def run_onnx_model(model_path, image_path, img_size=320):
    """Run inference with YOLOv11 ONNX model (.onnx) on an image."""
    try:
        # If image_path is a directory, get the most recent image
        if os.path.isdir(image_path):
            image_path = get_most_recent_image(image_path)
            if image_path is None:
                print(f"Error: No image files found in directory")
                return
            print(f"Processing most recent image: {os.path.basename(image_path)}")
        
        if not os.path.exists(image_path):
            print(f"Error: Image file {image_path} not found")
            return
        
        if not os.path.exists(model_path):
            print(f"Error: Model file {model_path} not found")
            return
        
        session = ort.InferenceSession(model_path)
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Failed to load image {image_path}")
            return

        # Store original dimensions for scaling
        orig_h, orig_w = img.shape[:2]
# '''
#     original implementation
#         # Preprocess image
#         img_resized = cv2.resize(img, (img_size, img_size))
#         img_normalized = img_resized.transpose(2, 0, 1).astype(np.float32) / 255.0
#         img_input = np.expand_dims(img_normalized, axis=0)
# '''

        # Preprocess image
        img_resized = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
        img_resized = cv2.resize(img_resized, (320, 320), interpolation=cv2.INTER_AREA)  # Resize to 320x320
        img_normalized = img_resized.transpose(2, 0, 1).astype(np.float32) / 255.0  # Transpose to CHW and normalize
        img_input = np.expand_dims(img_normalized, axis=0)  # Add batch dimension

        # Run inference
        outputs = session.run(None, {session.get_inputs()[0].name: img_input})[0]

        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "/home/cabs/Thesis/raspberrypi-app/images/annotated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get original filename without extension
        original_name = os.path.splitext(os.path.basename(image_path))[0]
        output_filename = f"{original_name}_onnx_annotated_{timestamp}.jpg"
        output_path = os.path.join(output_dir, output_filename)

        # Basic post-processing
        detections = outputs
        detection_count = 0
        detected_stages = set()
        
        # Use original image for annotation to maintain quality
        result_img = img.copy()
        
        for det in detections:
            if len(det) >= 6:  # Assuming [x1, y1, x2, y2, conf, class]
                conf = det[4]
                class_id = int(det[5])
                
                if conf > 0.25:
                    # Scale coordinates back to original image size
                    x1 = int(det[0] * orig_w / img_size)
                    y1 = int(det[1] * orig_h / img_size)
                    x2 = int(det[2] * orig_w / img_size)
                    y2 = int(det[3] * orig_h / img_size)
                    
                    # Draw bounding box
                    cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add confidence text
                    label = f"Class {class_id}: {conf:.2f}"
                    cv2.putText(result_img, label, (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    detection_count += 1
                    
                    # Track stages (assuming class_id 0=Stage1, 1=Stage2, 2=Stage3)
                    # Adjust this mapping based on your model's class mapping
                    if class_id == 0:  # Stage 1
                        detected_stages.add(1)
                    elif class_id == 1:  # Stage 2
                        detected_stages.add(2)
                    elif class_id == 2:  # Stage 3
                        detected_stages.add(3)

        # Save result
        success = cv2.imwrite(output_path, result_img)
        if success:
            print(f"Result successfully saved to {output_path}")
            if detection_count > 0:
                print(f"Detected {detection_count} object(s) with confidence > 0.25")
                
                # Determine overall growth stage (highest stage detected)
                if detected_stages:
                    growth_stage = max(detected_stages)
                    print(f"\nGrowth Stage: {growth_stage}")
                else:
                    print("\nGrowth Stage: Unknown")
            else:
                print("No objects detected")
        else:
            print(f"Error: Failed to save image to {output_path}")
            
    except Exception as e:
        print(f"Error in ONNX inference: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Detect tomatoes using YOLOv11 on Raspberry Pi")
    parser.add_argument("--model-type", choices=["pytorch", "onnx"], default="pytorch", 
                        help="Model type: pytorch (.pt) or onnx (.onnx)")
    parser.add_argument("--model-path", 
                        default="/home/cabs/Thesis/raspberrypi-app/services/runs/detect/train/weights/best.pt", 
                        help="Path to model file")
    parser.add_argument("--image-path", 
                        default=IMAGE_DIR, 
                        help="Path to input image or directory containing images")
    parser.add_argument("--img-size", type=int, default=320, 
                        help="Input image size")
    args = parser.parse_args()

    print(f"Starting {args.model_type.upper()} inference...")
    print(f"Model: {args.model_path}")
    print(f"Image source: {args.image_path}")
    print(f"Image size: {args.img_size}")
    print("-" * 50)

    if args.model_type == "pytorch":
        run_pytorch_model(args.model_path, args.image_path, args.img_size)
    else:
        run_onnx_model(args.model_path, args.image_path, args.img_size)

if __name__ == "__main__":
    main()