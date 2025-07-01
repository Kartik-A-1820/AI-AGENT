from langchain.tools import tool
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import json
import time

AGENT_DIR = "agent_working"

@tool
def generate_image_from_prompt(prompt: str, filename: str = "output.png") -> str:
    """
    Generates an image with Gemini 2.0 Flash preview and saves it, with retries.
    """
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "❌ GEMINI_API_KEY not set."

    client = genai.Client(api_key=key)
    model_id = "gemini-2.0-flash-preview-image-generation"
    cfg = types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])

    retries = 3
    for i in range(retries):
        try:
            # Add a small delay to avoid overwhelming the API
            time.sleep(2)

            resp = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=cfg
            )

            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                filename += ".png"

            os.makedirs(os.path.join(AGENT_DIR, "images"), exist_ok=True)
            path = os.path.join(AGENT_DIR, "images", filename)

            for part in resp.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    img.save(path)
                    return f"✅ Saved image → {path}"

            # If no image is returned, log it and possibly retry
            raw = json.dumps(type(resp).to_dict(resp), indent=2)
            print(f"⚠️ Model returned no image on attempt {i+1}. Raw response:\n{raw}")

        except Exception as e:
            print(f"An error occurred on attempt {i+1}: {e}")
            if i < retries - 1:
                print("Retrying...")
                time.sleep(5)  # Wait longer before retrying
            else:
                return f"❌ Failed to generate image after {retries} attempts."

    return f"⚠️ Failed to generate image after {retries} attempts."


