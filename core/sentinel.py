"""
Security Sentinel - Skener bezbednosti za generisani kod.
Detektuje potencijalno opasne konstrukte pre nego što se kod izvrši ili upiše na disk.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SecurityThreat:
    """Predstavlja detektovanu bezbednosnu pretnju."""
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    category: str  # 'SQL_INJECTION', 'XSS', 'CODE_EXECUTION', 'UNSAFE_LIBRARY', 'PRIVILEGE_ESCALATION'
    description: str
    line_number: int
    code_snippet: str


class SecuritySentinel:
    """
    Skener bezbednosti koji analizira generisani kod na poznate ranjivosti.
    
    Detektuje:
    - SQL Injection ranjivosti
    - XSS (Cross-Site Scripting) vektore
    - Nesigurno izvršavanje koda (eval, exec, compile)
    - Opasne sistemske komande
    - Nesigurne biblioteke
    - Pokušaje eskalacije privilegija
    """
    
    # Crvene zastavice - opasni paterni
    CRITICAL_PATTERNS = {
        'CODE_EXECUTION': [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bcompile\s*\(',
            r'__import__\s*\(',
        ],
        'SQL_INJECTION': [
            r'execute\s*\(\s*["\'].*%s.*["\']',  # String formatting u SQL
            r'execute\s*\(\s*f["\']',  # f-string u SQL
            r'execute\s*\(\s*.*\+.*\)',  # Konkatenacija u SQL
            r'cursor\.execute\s*\(.*\.format\(',  # .format() u SQL
        ],
        'XSS': [
            r'innerHTML\s*=',
            r'document\.write\s*\(',
            r'eval\s*\(\s*.*request',
        ],
        'UNSAFE_SYSTEM': [
            r'\bos\.system\s*\(',
            r'\bsubprocess\.call\s*\(.*shell\s*=\s*True',
            r'\bsubprocess\.run\s*\(.*shell\s*=\s*True',
            r'\bsubprocess\.Popen\s*\(.*shell\s*=\s*True',
        ],
        'PRIVILEGE_ESCALATION': [
            r'\bsudo\b',
            r'\bsu\s+root',
            r'os\.setuid\s*\(\s*0\s*\)',
            r'runas\s+/user:administrator',
        ],
        'UNSAFE_DESERIALIZATION': [
            r'\bpickle\.loads\s*\(',
            r'\byaml\.load\s*\(',  # bez safe_load
            r'\bmarshal\.loads\s*\(',
        ],
    }
    
    # Upozorenja - potencijalno problematični paterni
    WARNING_PATTERNS = {
        'UNSAFE_LIBRARY': [
            r'import\s+pickle\b',
            r'from\s+pickle\s+import',
            r'import\s+marshal\b',
        ],
        'NETWORK_RISK': [
            r'requests\.get\s*\(.*verify\s*=\s*False',
            r'urllib\.request\.urlopen\s*\(',
        ],
        'FILE_OPERATIONS': [
            r'open\s*\(.*["\']w["\']',  # Pisanje bez validacije
            r'os\.remove\s*\(',
            r'shutil\.rmtree\s*\(',
        ],
    }
    
    def __init__(self):
        """Inicijalizuje Security Sentinel."""
        self.threats: List[SecurityThreat] = []
    
    def scan_code(self, code: str) -> Tuple[bool, List[SecurityThreat]]:
        """
        Skenira kod na bezbednosne pretnje.
        
        Args:
            code: String sa Python kodom za analizu.
            
        Returns:
            Tuple (is_safe, threats) gde je:
            - is_safe: True ako kod ne sadrži kritične pretnje
            - threats: Lista detektovanih pretnji
        """
        self.threats = []
        lines = code.split('\n')
        
        # Skeniraj kritične paterne
        for category, patterns in self.CRITICAL_PATTERNS.items():
            self._scan_patterns(lines, patterns, category, 'CRITICAL')
        
        # Skeniraj upozorenja
        for category, patterns in self.WARNING_PATTERNS.items():
            self._scan_patterns(lines, patterns, category, 'MEDIUM')
        
        # Proveri da li postoje kritične pretnje
        critical_threats = [t for t in self.threats if t.severity == 'CRITICAL']
        is_safe = len(critical_threats) == 0
        
        return is_safe, self.threats
    
    def _scan_patterns(self, lines: List[str], patterns: List[str], 
                      category: str, severity: str) -> None:
        """
        Skenira linije koda na osnovu regex paterna.
        
        Args:
            lines: Liste linija koda.
            patterns: Lista regex paterna za pretragu.
            category: Kategorija pretnje.
            severity: Nivo ozbiljnosti.
        """
        for line_num, line in enumerate(lines, start=1):
            # Preskoči komentare
            if line.strip().startswith('#'):
                continue
            
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    threat = SecurityThreat(
                        severity=severity,
                        category=category,
                        description=self._get_threat_description(category, pattern),
                        line_number=line_num,
                        code_snippet=line.strip()
                    )
                    self.threats.append(threat)
    
    def _get_threat_description(self, category: str, pattern: str) -> str:
        """Vraća opis pretnje na osnovu kategorije."""
        descriptions = {
            'CODE_EXECUTION': 'Detektovano nesigurno izvršavanje koda (eval/exec/compile)',
            'SQL_INJECTION': 'Potencijalna SQL Injection ranjivost - koristi parametrizovane upite',
            'XSS': 'Potencijalna XSS ranjivost - sanitizuj korisnički unos',
            'UNSAFE_SYSTEM': 'Opasna sistemska komanda - izbegavaj shell=True',
            'PRIVILEGE_ESCALATION': 'Pokušaj eskalacije privilegija detektovan',
            'UNSAFE_DESERIALIZATION': 'Nesigurna deserijalizacija - koristi safe_load ili json',
            'UNSAFE_LIBRARY': 'Uvoz potencijalno nesigurne biblioteke',
            'NETWORK_RISK': 'Nesiguran mrežni zahtev - proveri SSL verifikaciju',
            'FILE_OPERATIONS': 'Operacija sa fajlovima bez validacije putanje',
        }
        return descriptions.get(category, 'Nepoznata bezbednosna pretnja')
    
    def generate_report(self) -> str:
        """
        Generiše čitljiv izveštaj o detektovanim pretnjama.
        
        Returns:
            Formatiran string sa izveštajem.
        """
        if not self.threats:
            return "✓ Kod je bezbedan - nisu detektovane pretnje."
        
        report = ["\n" + "="*70]
        report.append("🚨 SECURITY SENTINEL - IZVEŠTAJ O PRETNJAMA")
        report.append("="*70 + "\n")
        
        # Grupiši po ozbiljnosti
        by_severity = {}
        for threat in self.threats:
            by_severity.setdefault(threat.severity, []).append(threat)
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity in by_severity:
                report.append(f"\n[{severity}] Detektovano: {len(by_severity[severity])} pretnji\n")
                for threat in by_severity[severity]:
                    report.append(f"  Linija {threat.line_number}: {threat.description}")
                    report.append(f"  Kategorija: {threat.category}")
                    report.append(f"  Kod: {threat.code_snippet}")
                    report.append("")
        
        report.append("="*70)
        return "\n".join(report)
