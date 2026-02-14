"""
Secure Orchestrator - Mozak AI Fabrike sa ugrađenom bezbednosnom validacijom.
Koordinira LLM pozive, validaciju koda i bezbedno izvršavanje.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import litellm

from core.sentinel import SecuritySentinel, SecurityThreat
from tools.file_manager import FileManager, SecurityError


# Učitaj environment varijable
load_dotenv()


class SecureOrchestrator:
    """
    Glavni orkestrator koji upravlja celim procesom generisanja koda.
    
    Workflow:
    1. Korisnički zahtev
    2. LLM generiše plan
    3. LLM generiše kod
    4. Security Sentinel skenira kod
    5. Ako je bezbedan -> FileManager upisuje
    6. Ako nije -> LLM dobija feedback i pokušava ponovo
    """
    
    def __init__(self, project_dir: Optional[str] = None, max_retries: int = 3):
        """
        Inicijalizuje Secure Orchestrator.
        
        Args:
            project_dir: Radni direktorijum projekta.
            max_retries: Maksimalan broj pokušaja prepravke nesigurnog koda.
        """
        self.file_manager = FileManager(project_dir)
        self.sentinel = SecuritySentinel()
        self.max_retries = max_retries
        self.total_tokens_used = 0
        
        # Podrazumevani model (može se promeniti)
        self.model = os.getenv('DEFAULT_LLM_MODEL', 'gpt-4o-mini')
        
        print(f"[Orchestrator] Inicijalizovan sa modelom: {self.model}")
        print(f"[Orchestrator] Radni direktorijum: {self.file_manager.BASE_DIR}")
    
    def generate_and_validate_code(self, prompt: str, filename: str) -> Dict[str, Any]:
        """
        Generiše kod pomoću LLM-a i validira ga kroz Security Sentinel.
        
        Args:
            prompt: Prompt za LLM.
            filename: Ime fajla u koji će kod biti upisan (relativna putanja).
            
        Returns:
            Dict sa statusom, kodom, pretnjama i metrikama.
        """
        result = {
            'success': False,
            'code': None,
            'threats': [],
            'attempts': 0,
            'tokens_used': 0,
            'message': ''
        }
        
        for attempt in range(1, self.max_retries + 1):
            result['attempts'] = attempt
            print(f"\n[Orchestrator] Pokušaj {attempt}/{self.max_retries} - Generisanje koda...")
            
            # Generiši kod pomoću LLM-a
            try:
                generated_code, tokens = self._call_llm(prompt)
                result['tokens_used'] += tokens
                self.total_tokens_used += tokens
            except Exception as e:
                result['message'] = f"Greška pri pozivu LLM-a: {str(e)}"
                print(f"[Orchestrator] ✗ {result['message']}")
                continue
            
            # Skeniraj kod kroz Security Sentinel
            is_safe, threats = self.sentinel.scan_code(generated_code)
            result['threats'] = threats
            
            if is_safe:
                # Kod je bezbedan - upiši ga
                try:
                    self.file_manager.safe_write(filename, generated_code)
                    result['success'] = True
                    result['code'] = generated_code
                    result['message'] = f'Kod uspešno generisan i upisan u {filename}'
                    print(f"[Orchestrator] ✓ {result['message']}")
                    return result
                except SecurityError as e:
                    result['message'] = f"Bezbednosna greška pri upisu: {str(e)}"
                    print(f"[Orchestrator] ✗ {result['message']}")
                    return result
            else:
                # Kod nije bezbedan - pripremi feedback za LLM
                print(f"[Orchestrator] ✗ Kod sadrži bezbednosne pretnje!")
                print(self.sentinel.generate_report())
                
                if attempt < self.max_retries:
                    # Pripremi prompt za prepravku
                    prompt = self._create_fix_prompt(prompt, generated_code, threats)
                    print(f"[Orchestrator] Tražim od LLM-a da prepravi kod...")
        
        # Maksimalan broj pokušaja iscrpljen
        result['message'] = f'Kod nije mogao biti generisan bezbedno nakon {self.max_retries} pokušaja'
        print(f"[Orchestrator] ✗ {result['message']}")
        return result
    
    def _call_llm(self, prompt: str) -> tuple[str, int]:
        """
        Poziva LLM preko litellm biblioteke.
        
        Args:
            prompt: Prompt za model.
            
        Returns:
            Tuple (generisani_kod, broj_tokena).
        """
        response = litellm.completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Ti si ekspert Python programer. Generiši samo čist, bezbedan kod bez objašnjenja."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Niža temperatura za deterministički kod
        )
        
        code = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        # Ukloni markdown code fences ako postoje
        if code.startswith('```'):
            lines = code.split('\n')
            code = '\n'.join(lines[1:-1]) if lines[-1].startswith('```') else '\n'.join(lines[1:])
        
        return code.strip(), tokens
    
    def _create_fix_prompt(self, original_prompt: str, unsafe_code: str, 
                          threats: List[SecurityThreat]) -> str:
        """
        Kreira prompt za LLM da prepravi nesiguran kod.
        
        Args:
            original_prompt: Originalni zahtev.
            unsafe_code: Generisani nesiguran kod.
            threats: Lista detektovanih pretnji.
            
        Returns:
            Novi prompt sa instrukcijama za prepravku.
        """
        threat_descriptions = "\n".join([
            f"- Linija {t.line_number}: {t.description} ({t.category})"
            for t in threats if t.severity == 'CRITICAL'
        ])
        
        fix_prompt = f"""
ORIGINALNI ZAHTEV:
{original_prompt}

GENERISANI KOD SADRŽI BEZBEDNOSNE RANJIVOSTI:
{threat_descriptions}

INSTRUKCIJE ZA PREPRAVKU:
1. Ukloni sve eval(), exec(), compile() pozive
2. Koristi parametrizovane SQL upite (?, placeholders)
3. Izbegavaj shell=True u subprocess pozivima
4. Koristi safe_load umesto load za YAML
5. Validiraj sve korisničke unose
6. Nikada ne koristi sudo ili privilegovane komande

Generiši ISPRAVAN i BEZBEDAN kod koji ispunjava originalni zahtev.
"""
        return fix_prompt
    
    def get_token_usage(self) -> int:
        """Vraća ukupan broj utrošenih tokena."""
        return self.total_tokens_used
