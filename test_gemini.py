import os
import litellm
from dotenv import load_dotenv

# Učitaj .env fajl
load_dotenv()

# Uzmi ključ iz .env
key = os.getenv('GOOGLE_API_KEY')

# LiteLLM za Gemini modele primarno traži GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = key

# Uključi debug ako želiš detaljan ispis (opciono)
litellm.set_verbose = True 

models_to_test = [
    "gemini/gemini-1.5-flash",
    "gemini/gemini-1.5-pro",
]

for model in models_to_test:
    print(f"\n--- Testiranje modela: {model} ---")
    try:
        # Kod LiteLLM-a, ako koristiš "gemini/" prefiks, 
        # on će automatski tražiti GEMINI_API_KEY iz environment-a
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "Zdravo, test konekcije."}]
        )
        
        print(f"✓ Uspeh sa {model}!")
        print(f"Odgovor: {response.choices[0].message.content}")
        # Ako jedan model proradi, prekidamo petlju
        break
        
    except Exception as e:
        print(f"✗ Greška sa {model}: {str(e)}")

# Napomena: Ako i dalje dobijaš grešku, proveri da li je 
# tvoj API ključ validan na Google AI Studio portalu.