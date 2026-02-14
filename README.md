# 🏭 AI Fabrika - Master Prompt v3.0

**Sigurna AI Fabrika sa ugrađenim bezbednosnim slojevima**

## 🛡️ Bezbednosne Karakteristike

### 1. **Path Sanitizer** (FileManager)
- ✅ Blokira Directory Traversal napade
- ✅ Ograničava pristup samo na radni folder projekta
- ✅ Automatska validacija svih putanja

### 2. **Security Sentinel** (Code Scanner)
- ✅ Detektuje SQL Injection ranjivosti
- ✅ Detektuje XSS vektore
- ✅ Blokira nesigurno izvršavanje koda (`eval`, `exec`)
- ✅ Detektuje opasne sistemske komande
- ✅ Proverava nesigurne biblioteke
- ✅ Sprečava eskalaciju privilegija

### 3. **Secure Orchestrator**
- ✅ Automatska validacija pre upisa koda
- ✅ Retry mehanizam sa feedback loop-om
- ✅ Token tracking i optimizacija

## 📦 Instalacija

```bash
# 1. Instaliraj zavisnosti
pip install -r requirements.txt

# 2. Kopiraj i konfiguriši environment varijable
copy .env.example .env
# Edituj .env i dodaj svoj API key
```

## 🚀 Pokretanje

```bash
python main.py
```

## 📁 Struktura Projekta

```
setup_factory.py/
├── core/
│   ├── __init__.py
│   ├── orchestrator.py    # Secure Orchestrator - mozak sistema
│   └── sentinel.py         # Security Sentinel - skener koda
├── tools/
│   ├── __init__.py
│   └── file_manager.py     # FileManager sa Path Sanitizer-om
├── generated/              # Ovde se kreiraju generisani fajlovi
├── main.py                 # CLI interfejs
├── requirements.txt
├── .env.example
└── README.md
```

## 🔒 Kako Funkcioniše Bezbednost?

### Workflow:

1. **Korisnički zahtev** → LLM generiše kod
2. **Security Sentinel** → Skenira kod na ranjivosti
3. **Ako je bezbedan** → FileManager upisuje (sa Path Sanitizer proverom)
4. **Ako nije bezbedan** → LLM dobija feedback i pokušava ponovo (max 3 puta)

### Primer Blokiranog Koda:

```python
# ❌ BLOKIRANO - Nesigurno izvršavanje
user_input = input("Unesi komandu: ")
eval(user_input)  # CRITICAL: CODE_EXECUTION

# ❌ BLOKIRANO - SQL Injection
query = f"SELECT * FROM users WHERE id = {user_id}"  # CRITICAL: SQL_INJECTION

# ❌ BLOKIRANO - Directory Traversal
file_manager.safe_write("../../etc/passwd", "hack")  # SecurityError!
```

### Primer Bezbednog Koda:

```python
# ✅ ODOBRENO - Parametrizovani upit
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ✅ ODOBRENO - Validiran unos
sanitized_input = sanitize_input(user_input)

# ✅ ODOBRENO - Putanja unutar projekta
file_manager.safe_write("generated/utils.py", code)
```

## 📊 Primer Izlaza

```
🏭 AI FABRIKA - Master Prompt v3.0
======================================================================
📁 Radni direktorijum: D:\setup_factory.py
🤖 LLM Model: gpt-4o-mini
🛡️  Bezbednosni sloj: AKTIVAN
======================================================================

📝 Zadatak: Kreiraj 'generated/utils.py'
💭 Prompt: Kreiraj helper funkcije...

[Orchestrator] Pokušaj 1/3 - Generisanje koda...
[FileManager] ✓ Fajl uspešno kreiran: generated\utils.py
[Orchestrator] ✓ Kod uspešno generisan i upisan u generated/utils.py

----------------------------------------------------------------------
📊 REZULTAT GENERISANJA
----------------------------------------------------------------------
Fajl: generated/utils.py
Status: ✓ USPEŠNO
Pokušaji: 1
Tokeni: 450
Poruka: Kod uspešno generisan i upisan u generated/utils.py

✓ Security Health Check: PASSED
----------------------------------------------------------------------
```

## 🎯 Primeri Upotrebe

### Primer 1: Kreiraj Bezbedni Helper Modul

```python
factory.create_file(
    prompt="Kreiraj utils.py sa funkcijama za validaciju email-a i sanitizaciju unosa",
    filename="generated/utils.py"
)
```

### Primer 2: Kreiraj Database Modul

```python
factory.create_file(
    prompt="Kreiraj database.py sa parametrizovanim SQL upitima",
    filename="generated/database.py"
)
```

## ⚙️ Konfiguracija

### Environment Varijable (.env)

```bash
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=gpt-4o-mini
```

### Podržani Modeli (preko litellm)

- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- Google: `gemini/gemini-pro`
- I mnogi drugi...

## 🧪 Testiranje Bezbednosti

```python
from core.sentinel import SecuritySentinel

sentinel = SecuritySentinel()

# Test nesigurnog koda
unsafe_code = """
user_input = input()
eval(user_input)
"""

is_safe, threats = sentinel.scan_code(unsafe_code)
print(sentinel.generate_report())
```

## 📝 Napomene

- **Token Optimizacija**: Koristi temperature=0.3 za deterministički kod
- **Retry Mehanizam**: Maksimalno 3 pokušaja za generisanje bezbednog koda
- **Least Privilege**: Kod ne može koristiti `sudo`, `admin` ili opasne sistemske komande
- **Automatska Validacija**: Svaki generisani kod prolazi kroz Security Sentinel pre upisa

## 🤝 Doprinos

Ova AI Fabrika je dizajnirana sa bezbednošću kao prioritetom. Ako pronađeš novu ranjivost ili imaš ideju za poboljšanje, slobodno doprinesi!

## 📄 Licenca

MIT License - Slobodno koristi i modifikuj.

---

**Napravljeno sa ❤️ i 🛡️ bezbednošću na umu**
