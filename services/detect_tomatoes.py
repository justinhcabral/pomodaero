# import cv2
# import numpy as np
# import onnxruntime as ort
# import os 

# # Load the ONNX model
# # session = ort.InferenceSession("./best.onnx")
# onnx_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "best.onnx"))
# session = ort.InferenceSession(onnx_path)

# # Initialize the camera
# cap = cv2.VideoCapture(0)  # 0 for default camera
# if not cap.isOpened():
#     print("Error: Could not open camera.")
#     exit()

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         print("Error: Could not read frame.")
#         break

#     # Preprocess the image (resize to the input size expected by your model, typically 640x640 for YOLO)
#     input_size = (640, 640)
#     img = cv2.resize(frame, input_size)
#     img = img.astype(np.float32) / 255.0  # Normalize to [0,1]
#     img = np.transpose(img, (2, 0, 1))  # Change to CHW format
#     img = np.expand_dims(img, axis=0)  # Add batch dimension

#     # Run inference
#     inputs = {session.get_inputs()[0].name: img}
#     outputs = session.run(None, inputs)[0]

#     # Post-process the outputs (this depends on your model's output format)
#     # YOLO typically outputs [boxes, scores, classes]
#     # For simplicity, let's assume a confidence threshold
#     conf_threshold = 0.5
#     for detection in outputs:
#         confidence = detection[4]  # Assuming confidence score is at index 4
#         if confidence > conf_threshold:
#             class_id = int(detection[5])  # Assuming class ID is at index 5
#             if class_id == 0:  # Assuming 0 is the class ID for tomatoes
#                 x, y, w, h = detection[:4]  # Bounding box coordinates
#                 x, y, w, h = int(x), int(y), int(w), int(h)
#                 cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
#                 cv2.putText(frame, "Tomato", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

#     # Display the frame
#     cv2.imshow("Tomato Detection", frame)

#     # Break the loop on 'q' key press
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # Release resources
# cap.release()
# cv2.destroyAllWindows()

# single image capture test

import cv2
import numpy as np
import onnxruntime as ort
import os

# Load the ONNX model
onnx_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "best.onnx"))
session = ort.InferenceSession(onnx_path)

# Load the tomato plant image
image_path = "/home/cabs/Thesis/raspberrypi-app/services/tomato.jpeg"  # Update with your image path
frame = cv2.imread(image_path)
if frame is None:
    print(f"Error: Could not load image at {image_path}")
    exit()

# Preprocess the image (resize to the input size expected by your model, typically 640x640 for YOLO)
input_size = (640, 640)
img = cv2.resize(frame, input_size)
img = img.astype(np.float32) / 255.0  # Normalize to [0,1]
img = np.transpose(img, (2, 0, 1))  # Change to CHW format
img = np.expand_dims(img, axis=0)  # Add batch dimension

# Run inference
inputs = {session.get_inputs()[0].name: img}
outputs = session.run(None, inputs)[0]
print(f"Outputs shape: {outputs.shape}")  # Debug: Inspect output shape

# Post-process the outputs
conf_threshold = 0.5
for detection in outputs:
    print(f"Detection shape: {detection.shape}")  # Debug: Inspect each detection
    # Assume detection is [x, y, w, h, objectness_score, class_score_1, class_score_2, ...]
    objectness_score = detection[4]  # Objectness score (confidence of detection)
    class_scores = detection[5:]  # Class scores for all classes
    max_class_score = np.max(class_scores)  # Get highest class score
    class_id = np.argmax(class_scores)  # Get class ID with highest score

    # Combine objectness and class score for final confidence (common in YOLO)
    confidence = objectness_score * max_class_score if objectness_score < 1.0 else max_class_score

    if confidence > conf_threshold:
        if class_id == 0:  # Assuming 0 is the class ID for tomatoes
            x, y, w, h = detection[:4]  # Bounding box coordinates
            # Scale bounding box back to original image size
            scale_x = frame.shape[1] / input_size[0]
            scale_y = frame.shape[0] / input_size[1]
            x, y, w, h = int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Tomato: {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

# Save the output image
output_path = "output_tomato_plant.jpg"
cv2.imwrite(output_path, frame)
print(f"Output saved as {output_path}")

# Display the result (optional, requires a monitor or X11 forwarding)
try:
    cv2.imshow("Tomato Detection", frame)
    cv2.waitKey(0)  # Wait for any key press to close the window
except Exception as e:
    print(f"Error displaying image: {e}. Output saved to {output_path}")

# Release resources
cv2.destroyAllWindows()