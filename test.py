from google import genai, genai
from google.genai.types import GenerateContentConfig
from io import BytesIO
from PIL import Image
import base64, os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
resp = client.models.generate_content(
    model="gemini-2.0-flash-preview-image-generation",
    contents="A cute calico cat sitting on a red cushion",
    config=GenerateContentConfig(response_modalities=['TEXT','IMAGE'])
)
for p in resp.candidates[0].content.parts:
    if p.inline_data:
        Image.open(BytesIO(p.inline_data.data)).show()