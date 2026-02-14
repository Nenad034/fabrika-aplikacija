"""
FileManager - Bezbedni alat za rad sa fajlovima sa ugrađenim Path Sanitizer-om.
Sprečava Directory Traversal napade i ograničava pristup samo na radni folder projekta.
"""

import os
from pathlib import Path
from typing import Optional


class SecurityError(Exception):
    """Izuzetak koji se baca kada se detektuje bezbednosni rizik."""
    pass


class FileManager:
    """
    Bezbedni menadžer fajlova sa ugrađenom zaštitom od Directory Traversal napada.
    
    Attributes:
        BASE_DIR: Osnovni direktorijum projekta - sve operacije moraju biti unutar njega.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Inicijalizuje FileManager sa definisanim radnim direktorijumom.
        
        Args:
            base_dir: Osnovni direktorijum projekta. Ako nije naveden, koristi trenutni direktorijum.
        """
        if base_dir is None:
            self.BASE_DIR = Path.cwd()
        else:
            self.BASE_DIR = Path(base_dir).resolve()
        
        # Kreiraj BASE_DIR ako ne postoji
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"[FileManager] Radni direktorijum postavljen na: {self.BASE_DIR}")
    
    def _sanitize_path(self, path: str) -> Path:
        """
        Sanitizuje putanju i proverava da li je unutar BASE_DIR.
        
        Args:
            path: Putanja za sanitizaciju.
            
        Returns:
            Validirana apsolutna putanja kao Path objekat.
            
        Raises:
            SecurityError: Ako putanja pokušava da izađe van BASE_DIR.
        """
        # Konvertuj u Path objekat i razreši relativne putanje
        target_path = (self.BASE_DIR / path).resolve()
        
        # Proveri da li je target_path unutar BASE_DIR
        try:
            target_path.relative_to(self.BASE_DIR)
        except ValueError:
            raise SecurityError(
                f"BEZBEDNOSNA GREŠKA: Pokušaj pristupa van radnog direktorijuma!\n"
                f"Tražena putanja: {target_path}\n"
                f"Dozvoljen direktorijum: {self.BASE_DIR}\n"
                f"Operacija je blokirana."
            )
        
        return target_path
    
    def safe_write(self, path: str, content: str, encoding: str = 'utf-8') -> bool:
        """
        Bezbedno upisuje sadržaj u fajl nakon sanitizacije putanje.
        
        Args:
            path: Relativna putanja fajla u odnosu na BASE_DIR.
            content: Sadržaj koji treba upisati.
            encoding: Encoding za fajl (default: utf-8).
            
        Returns:
            True ako je upis uspešan.
            
        Raises:
            SecurityError: Ako putanja nije bezbedna.
        """
        safe_path = self._sanitize_path(path)
        
        # Kreiraj parent direktorijume ako ne postoje
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Upiši sadržaj
        safe_path.write_text(content, encoding=encoding)
        
        print(f"[FileManager] ✓ Fajl uspešno kreiran: {safe_path.relative_to(self.BASE_DIR)}")
        return True
    
    def safe_read(self, path: str, encoding: str = 'utf-8') -> str:
        """
        Bezbedno čita sadržaj fajla nakon sanitizacije putanje.
        
        Args:
            path: Relativna putanja fajla u odnosu na BASE_DIR.
            encoding: Encoding za fajl (default: utf-8).
            
        Returns:
            Sadržaj fajla kao string.
            
        Raises:
            SecurityError: Ako putanja nije bezbedna.
            FileNotFoundError: Ako fajl ne postoji.
        """
        safe_path = self._sanitize_path(path)
        
        if not safe_path.exists():
            raise FileNotFoundError(f"Fajl ne postoji: {safe_path.relative_to(self.BASE_DIR)}")
        
        content = safe_path.read_text(encoding=encoding)
        print(f"[FileManager] ✓ Fajl uspešno pročitan: {safe_path.relative_to(self.BASE_DIR)}")
        return content
    
    def safe_mkdir(self, path: str) -> bool:
        """
        Bezbedno kreira direktorijum nakon sanitizacije putanje.
        
        Args:
            path: Relativna putanja direktorijuma u odnosu na BASE_DIR.
            
        Returns:
            True ako je kreiranje uspešno.
            
        Raises:
            SecurityError: Ako putanja nije bezbedna.
        """
        safe_path = self._sanitize_path(path)
        safe_path.mkdir(parents=True, exist_ok=True)
        
        print(f"[FileManager] ✓ Direktorijum kreiran: {safe_path.relative_to(self.BASE_DIR)}")
        return True
    
    def safe_exists(self, path: str) -> bool:
        """
        Bezbedno proverava da li fajl ili direktorijum postoji.
        
        Args:
            path: Relativna putanja u odnosu na BASE_DIR.
            
        Returns:
            True ako putanja postoji, False inače.
            
        Raises:
            SecurityError: Ako putanja nije bezbedna.
        """
        safe_path = self._sanitize_path(path)
        return safe_path.exists()
    
    def safe_delete(self, path: str) -> bool:
        """
        Bezbedno briše fajl nakon sanitizacije putanje.
        
        Args:
            path: Relativna putanja fajla u odnosu na BASE_DIR.
            
        Returns:
            True ako je brisanje uspešno.
            
        Raises:
            SecurityError: Ako putanja nije bezbedna.
        """
        safe_path = self._sanitize_path(path)
        
        if safe_path.exists():
            if safe_path.is_file():
                safe_path.unlink()
                print(f"[FileManager] ✓ Fajl obrisan: {safe_path.relative_to(self.BASE_DIR)}")
            else:
                raise ValueError(f"Putanja nije fajl: {safe_path.relative_to(self.BASE_DIR)}")
        
        return True
