import cv2
import numpy as np
import json
import re
from ultralytics import YOLO
import base64
import os
from groq import Groq

class LicensePlateRecognizer:
    def __init__(self, model_path, api_key=None):
        """
        Initialize the License Plate Recognizer with Groq VLM.
        
        Args:
            model_path (str): Path to the YOLO .pt model file.
            api_key (str): Groq API key.
        """
        self.model = YOLO(model_path)
        self.api_key = api_key
        if not self.api_key:
             raise ValueError("Groq API Key is required.")
        
        self.client = Groq(api_key=self.api_key)
        self.vlm_model = "meta-llama/llama-4-scout-17b-16e-instruct" 

    def preprocess_image(self, image_path):
        """
        Read and preprocess the image (basic checks).
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at {image_path}")
        return img

    def detect_plate(self, img):
        """
        Detect license plate using YOLO model.
        Returns:
            dict: Best plate crop and metadata.
        """
        results = self.model(img)
        
        plates = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = box.conf[0].cpu().numpy().astype(float)
                
                # Crop the plate
                plate_img = img[y1:y2, x1:x2]
                plates.append({'crop': plate_img, 'conf': conf, 'box': (x1, y1, x2, y2)})
        
        # Sort by confidence
        plates.sort(key=lambda x: x['conf'], reverse=True)
        return plates[0] if plates else None

    def encode_image(self, image):
        """
        Encode OpenCV image to base64 string.
        """
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')

    def recognize_with_groq(self, plate_img):
        """
        Send image to Groq API for VLM recognition.
        """
        base64_image = self.encode_image(plate_img)
        
        prompt = """
        Analyze this Tunisian license plate. 
        Extract the text and classify the type.
        
        Tunisian Plate Types:
        1. TN: "Numbers تونس Numbers" (e.g., 123 تونس 4567)
        2. RS: "ن ت" + Numbers
        3. GV: Numbers + " - " + Numbers
        
        Output strictly valid JSON with no markdown formatting:
        {
            "plate_text": "The normalized text (e.g. '123 تونس 4567')",
            "plate_type": "TN" or "RS" or "GV" or "Unknown",
            "confidence": 0.9 (estimated confidence 0-1)
        }
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.vlm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Tunisian License Plate Recognition expert. You output strictly JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1, # Low temperature for consistent formatting
                response_format={"type": "json_object"} # Force JSON if supported by model, otherwise prompt handles it
            )
            
            response_content = completion.choices[0].message.content
            return json.loads(response_content)
            
        except Exception as e:
            print(f"Groq VLM Error: {e}")
            return None

    def process(self, image_path):
        """
        Main pipeline execution.
        """
        try:
            img = self.preprocess_image(image_path)
            
            # 1. Detection
            plate_data = self.detect_plate(img)
            
            if not plate_data:
                return {
                    "plate_detected": False,
                    "reason": "No plate detected by YOLO"
                }
            
            # 2. VLM Recognition
            # We skip heavy OpenCV enhancement as VLMs are robust, 
            # but detected crop is used directly.
            result = self.recognize_with_groq(plate_data['crop'])
            
            if result:
                result['plate_detected'] = True
                result['yolo_confidence'] = float(plate_data['conf'])
                return result
            else:
                 return {
                    "plate_detected": True,
                    "reason": "VLM failed to parse text"
                }

        except Exception as e:
            return {
                "plate_detected": False,
                "reason": f"Processing error: {str(e)}"
            }

# Example Usage
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Tunisian License Plate Recognizer (Groq VLM)")
    parser.add_argument("image_path", nargs="?", help="Path to the vehicle image")
    parser.add_argument("--api_key", default=os.getenv("GROQ_API_KEY"), help="Groq API Key")
    parser.add_argument("--model", default=r"c:\Users\lenovo\Desktop\Computer_Vision\best-1 (1).pt", help="Path to YOLO model")

    args = parser.parse_args()

    if not args.image_path:
        print("Usage: python license_plate_recognizer.py <path_to_image> [--api_key KEY]")
        sys.exit(1)

    print(f"Loading YOLO from {args.model}...")
    try:
        recognizer = LicensePlateRecognizer(args.model, args.api_key)
        
        print(f"Processing {args.image_path}...")
        result = recognizer.process(args.image_path)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as main_e:
        print(f"Error: {main_e}")
