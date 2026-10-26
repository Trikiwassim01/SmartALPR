import os
import shutil
from fastapi import UploadFile

# Absolute import assuming 'Backend' is the CWD and in sys.path
try:
    from Computer_Vision.license_plate_recognizer import LicensePlateRecognizer
except ImportError:
    # Fallback or strict import
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../Computer_Vision'))
    from license_plate_recognizer import LicensePlateRecognizer

# Singleton instance
_recognizer = None

def get_recognizer():
    global _recognizer
    if _recognizer is None:
        # API Key (Should be in environment variables)
        api_key = os.getenv("GROQ_API_KEY")
        

        _recognizer = LicensePlateRecognizer(model_path=None, api_key=api_key)
    return _recognizer

async def analyze_vehicle_image(file: UploadFile):
    recognizer = get_recognizer()
    
    # Save temp file
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        result = recognizer.process(temp_path)
        return result
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
