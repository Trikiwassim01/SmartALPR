import cv2
import numpy as np
import json
import re
import base64
import os
from groq import Groq

class LicensePlateRecognizer:
    def __init__(self, model_path=None, api_key=None):
        """
        Initialize the License Plate Recognizer with Groq VLM.
        
        Args:
            model_path (str): Ignored now (formerly for YOLO).
            api_key (str): Groq API key.
        """
        self.api_key = api_key
        if not self.api_key:
             raise ValueError("Groq API Key is required.")
        
        self.client = Groq(api_key=self.api_key)
        self.vlm_model = "meta-llama/llama-4-scout-17b-16e-instruct" 
        # Fallback to previously working model if needed: meta-llama/llama-3.2-11b-vision-preview

    def preprocess_image(self, image_path):
        """
        Read the image.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at {image_path}")
        return img

    def encode_image(self, image):
        """
        Encode OpenCV image to base64 string.
        """
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')

    def recognize_with_groq(self, full_img):
        """
        Send full image to Groq API for VLM recognition.
        """
        base64_image = self.encode_image(full_img)
        
        prompt = """
        Analyze this image of a vehicle.
        1. Find the license plate.
        2. Extract the text from the license plate.
        3. Classify the type of the plate.
        
        Tunisian Plate Types:
        1. TN: "Numbers تونس Numbers" (e.g., 123 تونس 4567)
        2. RS: "ن ت" + Numbers
        3. GV: Numbers + " - " + Numbers
        
        Output strictly valid JSON with no markdown formatting:
        {
            "plate_detected": true/false,
            "plate_text": "The normalized text (e.g. '123 تونس 4567')",
            "plate_type": "TN" or "RS" or "GV" or "Unknown",
            "confidence": 0.9,
            "reason": "If not detected, why"
        }
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.vlm_model,
                messages=[
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
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            response_content = completion.choices[0].message.content
            return json.loads(response_content)
            
        except Exception as e:
            print(f"Groq VLM Error: {e}")
            return {
                "plate_detected": False,
                "reason": f"API Error: {str(e)}"
            }

    def process(self, image_path):
        """
        Main pipeline execution.
        """
        try:
            img = self.preprocess_image(image_path)
            
            # Send full image to Groq VLM
            result = self.recognize_with_groq(img)
            
            # Add compatibility fields expected by frontend if missing
            if result.get('plate_detected', False):
                result['yolo_confidence'] = result.get('confidence', 1.0)
            
            return result

        except Exception as e:
            return {
                "plate_detected": False,
                "reason": f"Processing error: {str(e)}"
            }
