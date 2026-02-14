import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=key)

print(f"Testiranje ključa: {key[:10]}...")

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Zdravo, test.")
    print("✓ Uspeh sa google-generativeai!")
    print(f"Odgovor: {response.text}")
except Exception as e:
    print(f"✗ Greška sa google-generativeai: {str(e)}")

print("\nListing available models:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Could not list models: {str(e)}")
