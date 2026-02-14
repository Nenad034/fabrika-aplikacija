import os

# Definicija strukture projekta
folders = [
    "core",
    "tools",
    "config",
    "output"
]

files = {
    "config/settings.py": "import os\nfrom dotenv import load_dotenv\nload_dotenv()\n\nAPI_KEYS = {\n    'anthropic': os.getenv('ANTHROPIC_API_KEY'),\n    'openai': os.getenv('OPENAI_API_KEY'),\n    'gemini': os.getenv('GOOGLE_API_KEY'),\n    'deepseek': os.getenv('DEEPSEEK_API_KEY')\n}",
    "tools/file_manager.py": "import os\n\nclass FileManager:\n    @staticmethod\n    def create_directory(path):\n        os.makedirs(path, exist_ok=True)\n        return f'✅ Folder kreiran: {path}'\n\n    @staticmethod\n    def write_file(path, content):\n        with open(path, 'w', encoding='utf-8') as f:\n            f.write(content)\n        return f'✅ Fajl upisan: {path}'",
    ".env": "ANTHROPIC_API_KEY=tvoj_kljuc_ovde\nOPENAI_API_KEY=tvoj_kljuc_ovde\nGOOGLE_API_KEY=tvoj_kljuc_ovde\nDEEPSEEK_API_KEY=tvoj_kljuc_ovde",
    "requirements.txt": "litellm\npython-dotenv\npydantic\nfastapi\nuvicorn"
}

def build():
    print("🏗️ Započinjem izgradnju AI Fabrike...")
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Složen folder: {folder}")
    
    for path, content in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Kreiran fajl: {path}")
    print("\n✅ Temelj je postavljen. Instaliraj biblioteke sa: pip install -r requirements.txt")

if __name__ == "__main__":
    build()