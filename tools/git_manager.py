"""
Git Manager
Alat za upravljanje Git operacijama (init, status, add, commit, push).
"""

import subprocess
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class GitManager:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
    
    def _run_git(self, args: List[str]) -> Tuple[bool, str]:
        """Izvršava git komandu u project_root direktorijumu."""
        try:
            # Provera da li git postoji
            result = subprocess.run(
                ['git'] + args,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except FileNotFoundError:
            return False, "Git nije instaliran ili nije u PATH-u."
        except Exception as e:
            return False, str(e)

    def is_git_initialized(self) -> bool:
        """Proverava da li je folder git repozitorijum."""
        return (self.project_root / '.git').exists()
    
    def init(self) -> Tuple[bool, str]:
        """Inicijalizuje git repozitorijum."""
        return self._run_git(['init'])
    
    def status(self) -> Dict[str, List[str]]:
        """
        Vraća status fajlova (modified, staged, untracked).
        Vraca dict sa listama fajlova.
        """
        success, output = self._run_git(['status', '--porcelain'])
        
        if not success:
            return {"error": output}
        
        staged = []
        modified = []
        untracked = []
        
        for line in output.split('\n'):
            if not line: continue
            
            # Format: XY Path
            # X = index status, Y = working tree status
            code = line[:2]
            path = line[3:]
            
            if code.startswith('M') or code.startswith('A'):
                staged.append(path)
            if code[1] == 'M':
                modified.append(path)
            if code.startswith('??'):
                untracked.append(path)
                
        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked
        }
    
    def add(self, files: List[str]) -> Tuple[bool, str]:
        """Dodaje fajlove u staging area."""
        return self._run_git(['add'] + files)
    
    def commit(self, message: str) -> Tuple[bool, str]:
        """Kreira commit sa datom porukom."""
        return self._run_git(['commit', '-m', message])
    
    def push(self, remote: str = 'origin', branch: str = 'main') -> Tuple[bool, str]:
        """Radi push na remote."""
        return self._run_git(['push', '-u', remote, branch])
    
    def set_remote(self, url: str, Name: str = 'origin') -> Tuple[bool, str]:
        """Postavlja remote URL."""
        # Prvo probaj da dodaš, ako postoji probaj set-url
        success, _ = self._run_git(['remote', 'add', Name, url])
        if not success:
            return self._run_git(['remote', 'set-url', Name, url])
        return True, "Remote set successfully"
    
    def get_config(self, key: str) -> Optional[str]:
        """Vraća vrednost git konfiguracije."""
        success, output = self._run_git(['config', '--get', key])
        return output if success else None

    def get_remotes(self) -> List[str]:
        """Vraća listu definisanih remote-ova."""
        success, output = self._run_git(['remote', '-v'])
        if success and output:
            return list(set(line.split()[0] for line in output.split('\n') if line))
        return []

    def get_branches(self) -> List[str]:
        """Vraća listu lokalnih grana."""
        success, output = self._run_git(['branch'])
        if success and output:
            return [line.strip().replace('* ', '') for line in output.split('\n') if line]
        return []
