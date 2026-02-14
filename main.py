"""
AI Fabrika - Glavni CLI interfejs sa bezbednosnim monitoringom.
Master Prompt v3.0 - Sigurna AI Fabrika sa Sanitizer i Security Sentinel zaštitom.
"""

import sys
from pathlib import Path
from typing import Optional

from core.orchestrator import SecureOrchestrator
from core.sentinel import SecuritySentinel
from tools.file_manager import FileManager


class AIFactory:
    """
    Glavni interfejs AI Fabrike.
    Prikazuje status, metrike i bezbednosne provere.
    """
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Inicijalizuje AI Fabriku.
        
        Args:
            project_dir: Radni direktorijum projekta.
        """
        self.orchestrator = SecureOrchestrator(project_dir)
        self.project_dir = self.orchestrator.file_manager.BASE_DIR
        
        print("\n" + "="*70)
        print("🏭 AI FABRIKA - Master Prompt v3.0")
        print("="*70)
        print(f"📁 Radni direktorijum: {self.project_dir}")
        print(f"🤖 LLM Model: {self.orchestrator.model}")
        print(f"🛡️  Bezbednosni sloj: AKTIVAN")
        print("="*70 + "\n")
    
    def create_file(self, prompt: str, filename: str) -> bool:
        """
        Kreira fajl sa generisanim kodom.
        
        Args:
            prompt: Opis šta fajl treba da radi.
            filename: Relativna putanja fajla.
            
        Returns:
            True ako je kreiranje uspešno.
        """
        print(f"\n📝 Zadatak: Kreiraj '{filename}'")
        print(f"💭 Prompt: {prompt}\n")
        
        result = self.orchestrator.generate_and_validate_code(prompt, filename)
        
        # Prikaži rezultat
        self._print_result(result, filename)
        
        return result['success']
    
    def _print_result(self, result: dict, filename: str) -> None:
        """Prikazuje rezultat generisanja."""
        print("\n" + "-"*70)
        print("📊 REZULTAT GENERISANJA")
        print("-"*70)
        print(f"Fajl: {filename}")
        print(f"Status: {'✓ USPEŠNO' if result['success'] else '✗ NEUSPEŠNO'}")
        print(f"Pokušaji: {result['attempts']}")
        print(f"Tokeni: {result['tokens_used']}")
        print(f"Poruka: {result['message']}")
        
        if result['threats']:
            print(f"\n🚨 Detektovano pretnji: {len(result['threats'])}")
            sentinel = SecuritySentinel()
            sentinel.threats = result['threats']
            print(sentinel.generate_report())
        else:
            print("\n✓ Security Health Check: PASSED")
        
        print("-"*70 + "\n")
    
    def show_status(self) -> None:
        """Prikazuje trenutni status fabrike."""
        print("\n" + "="*70)
        print("📈 STATUS AI FABRIKE")
        print("="*70)
        print(f"Ukupno utrošenih tokena: {self.orchestrator.get_token_usage()}")
        print(f"Radni direktorijum: {self.project_dir}")
        
        # Prikaži kreirane fajlove
        created_files = list(self.project_dir.rglob('*.py'))
        print(f"\nKreirano fajlova: {len(created_files)}")
        for f in created_files:
            rel_path = f.relative_to(self.project_dir)
            print(f"  ✓ {rel_path}")
        
        print("="*70 + "\n")


def main():
    """Glavna funkcija - demonstracija AI Fabrike."""
    
    # Kreiraj AI Fabriku u trenutnom direktorijumu
    factory = AIFactory()
    
    # Primer 1: Kreiraj helper modul
    factory.create_file(
        prompt="""
        Kreiraj Python modul 'utils.py' sa helper funkcijama:
        - validate_email(email: str) -> bool
        - sanitize_input(text: str) -> str
        - hash_password(password: str) -> str (koristi bcrypt)
        
        Sve funkcije moraju biti bezbedne i validovane.
        """,
        filename="generated/utils.py"
    )
    
    # Primer 2: Kreiraj database modul (sa parametrizovanim upitima)
    factory.create_file(
        prompt="""
        Kreiraj Python modul 'database.py' sa klasom DatabaseManager:
        - Metoda get_user(user_id: int) koja koristi parametrizovane upite
        - Metoda create_user(username: str, email: str) sa validacijom
        - Koristi sqlite3 sa bezbednim upitima (bez string konkatenacije)
        """,
        filename="generated/database.py"
    )
    
    # Prikaži finalni status
    factory.show_status()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 AI Fabrika zaustavljena.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Kritična greška: {e}")
        sys.exit(1)
