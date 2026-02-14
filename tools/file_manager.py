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
            base_dir: Osnovni direktorijum projekta.
        """
        if base_dir is None:
            self.BASE_DIR = Path.cwd()
        else:
            self.BASE_DIR = Path(base_dir).resolve()
        
        # SR: Multi-Root podrška
        # Čuvamo listu svih dozvoljenih korena (Project Roots)
        self.roots = [self.BASE_DIR]
        
        # Kreiraj BASE_DIR ako ne postoji
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"[FileManager] Radni direktorijum postavljen na: {self.BASE_DIR}")
        print(f"[FileManager] Aktivni koreni: {[str(r) for r in self.roots]}")

    def add_root(self, path: str) -> bool:
        """Dodaje novi folder u listu dozvoljenih korena."""
        try:
            p = Path(path).resolve()
            if not p.exists() or not p.is_dir():
                return False
            if p not in self.roots:
                self.roots.append(p)
                print(f"[FileManager] Dodat novi koren: {p}")
            return True
        except:
            return False

    def remove_root(self, path: str) -> bool:
        """Uklanja folder iz liste dozvoljenih korena (osim primarnog BASE_DIR)."""
        try:
            p = Path(path).resolve()
            if p in self.roots and p != self.roots[0]:
                self.roots.remove(p)
                print(f"[FileManager] Uklonjen koren: {p}")
                return True
            return False
        except:
            return False
    
    def _sanitize_path(self, path: str) -> Path:
        """
        Sanitizuje putanju i proverava da li je unutar BILO KOG dozvoljenog korena.
        """
        p = Path(path)
        
        # Ako je apsolutna, proveravamo direktno
        if p.is_absolute():
            resolved_path = Path(os.path.abspath(str(p)))
        else:
            # Ako je relativna, podrazumevano je vezujemo za BASE_DIR
            resolved_path = Path(os.path.abspath(str(self.BASE_DIR / p)))

        # Provera da li je unutar bilo kog korena
        is_safe = False
        for root in self.roots:
            try:
                if str(resolved_path).startswith(str(root)):
                    is_safe = True
                    break
            except:
                continue
        
        if not is_safe:
             roots_str = ", ".join([str(r) for r in self.roots])
             raise SecurityError(f"Pristup odbijen: {path} (Nije u dozvoljenim korenima)")
             
        return resolved_path
    
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
        """
        safe_path = self._sanitize_path(path)
        
        if safe_path.exists():
            if safe_path.is_file():
                safe_path.unlink()
                print(f"[FileManager] ✓ Fajl obrisan: {safe_path.relative_to(self.BASE_DIR)}")
            else:
                raise ValueError(f"Putanja nije fajl: {safe_path.relative_to(self.BASE_DIR)}")
        
        return True

    def list_files(self, max_depth: int = 10) -> list[str]:
        """
        Lista fajlove iz svih aktivnih korena.
        """
        exclude_dirs = {'.git', 'node_modules', '__pycache__', '.venv', '.history', '.agent', 'dist', 'build', 'venv', 'env'}
        files = []
        
        # Ako imamo više korena, vraćamo apsolutne putanje ili prefixovane
        use_absolute = len(self.roots) > 1

        for root in self.roots:
            def _scan(current_path: Path, current_depth: int):
                if current_depth > max_depth:
                    return
                
                try:
                    for item in current_path.iterdir():
                        if item.is_dir():
                            if item.name not in exclude_dirs and not item.name.startswith('.'):
                                _scan(item, current_depth + 1)
                        elif item.is_file():
                            # Filtriranje ekstenzija
                            if item.suffix.lower() in {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json', '.md', '.txt', '.yaml', '.yml'}:
                                path_str = str(item) if use_absolute else str(item.relative_to(self.BASE_DIR))
                                if path_str not in files:
                                    files.append(path_str)

                except Exception:
                    pass
                    
            _scan(root, 0)
            
        return sorted(list(set(files))) # SR: Extra safety set conversion
