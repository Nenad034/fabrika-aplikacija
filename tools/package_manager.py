"""
Package Manager Tool
Omogućava AI agentu da automatski instalira Python i Node.js zavisnosti.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, List, Dict

class PackageManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        
    def install_python(self, package: str) -> Tuple[bool, str]:
        """
        Instalira Python paket koristeći pip.
        
        Args:
            package: Ime paketa (npr. 'requests', 'pandas==1.5.0')
            
        Returns:
            (success, message)
        """
        try:
            # Bezbednosna provera - sprečava izvršavanje proizvoljnih komandi
            if any(char in package for char in [';', '&', '|', '`', '$', '(', ')']):
                return False, "Nevažeće ime paketa - detektovani opasni karakteri"
            
            print(f"[PackageManager] Instaliranje Python paketa: {package}")
            
            # Koristi sys.executable da osigura da instalira u ispravan Python environment
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return True, f"Uspešno instaliran: {package}\n{result.stdout}"
            else:
                return False, f"Greška pri instalaciji: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Instalacija prekinuta - timeout (120s)"
        except Exception as e:
            return False, f"Greška: {str(e)}"
    
    def install_node(self, package: str, dev: bool = False) -> Tuple[bool, str]:
        """
        Instalira Node.js paket koristeći npm.
        
        Args:
            package: Ime paketa (npr. 'react', 'axios@1.0.0')
            dev: Da li je dev dependency
            
        Returns:
            (success, message)
        """
        try:
            # Bezbednosna provera
            if any(char in package for char in [';', '&', '|', '`', '$', '(', ')']):
                return False, "Nevažeće ime paketa - detektovani opasni karakteri"
            
            print(f"[PackageManager] Instaliranje Node paketa: {package}")
            
            cmd = ['npm', 'install', package]
            if dev:
                cmd.append('--save-dev')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return True, f"Uspešno instaliran: {package}\n{result.stdout}"
            else:
                return False, f"Greška pri instalaciji: {result.stderr}"
                
        except FileNotFoundError:
            return False, "npm nije pronađen - instalirajte Node.js"
        except subprocess.TimeoutExpired:
            return False, "Instalacija prekinuta - timeout (180s)"
        except Exception as e:
            return False, f"Greška: {str(e)}"
    
    def check_python_package(self, package: str) -> Tuple[bool, str]:
        """
        Proverava da li je Python paket instaliran.
        
        Args:
            package: Ime paketa
            
        Returns:
            (installed, version_or_message)
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Izvuci verziju iz output-a
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        return True, version
                return True, "Instaliran (verzija nepoznata)"
            else:
                return False, "Nije instaliran"
                
        except Exception as e:
            return False, f"Greška pri proveri: {str(e)}"
    
    def check_node_package(self, package: str) -> Tuple[bool, str]:
        """
        Proverava da li je Node.js paket instaliran.
        
        Args:
            package: Ime paketa
            
        Returns:
            (installed, version_or_message)
        """
        try:
            package_json = self.project_root / 'package.json'
            
            if not package_json.exists():
                return False, "package.json ne postoji"
            
            import json
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Proveri u dependencies i devDependencies
            deps = data.get('dependencies', {})
            dev_deps = data.get('devDependencies', {})
            
            if package in deps:
                return True, deps[package]
            elif package in dev_deps:
                return True, f"{dev_deps[package]} (dev)"
            else:
                return False, "Nije instaliran"
                
        except Exception as e:
            return False, f"Greška pri proveri: {str(e)}"
    
    def list_python_packages(self) -> List[Dict[str, str]]:
        """
        Lista svih instaliranih Python paketa.
        
        Returns:
            Lista dict-ova sa 'name' i 'version'
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                return []
                
        except Exception as e:
            print(f"[PackageManager] Greška pri listanju paketa: {e}")
            return []
    
    def get_requirements(self) -> List[str]:
        """
        Čita requirements.txt fajl.
        
        Returns:
            Lista paketa iz requirements.txt
        """
        req_file = self.project_root / 'requirements.txt'
        
        if not req_file.exists():
            return []
        
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filtriraj komentare i prazne linije
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages.append(line)
            
            return packages
        except Exception as e:
            print(f"[PackageManager] Greška pri čitanju requirements.txt: {e}")
            return []
