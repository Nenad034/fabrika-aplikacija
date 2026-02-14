import os
import shutil
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Konfiguracija logging-a
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HistoryManager")

class HistoryManager:
    def __init__(self, base_dir: str, max_backups: int = 10):
        self.base_dir = Path(base_dir).resolve()
        self.history_dir = self.base_dir / ".history"
        self.max_backups = max_backups
        self._ensure_history_dir()

    def _ensure_history_dir(self):
        if not self.history_dir.exists():
            self.history_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, path: str) -> Optional[Path]:
        """
        Bezbedno razrešava putanju i osigurava da je unutar base_dir.
        Štiti od Path Traversal napada.
        """
        try:
            # Ako je path apsolutan i počinje sa base_dir, koristi ga, inače spoji
            if os.path.isabs(path):
                full_path = Path(path).resolve()
            else:
                full_path = (self.base_dir / path).resolve()
            
            if not str(full_path).startswith(str(self.base_dir)):
                logger.warning(f"Pokušaj pristupa van dozvoljenog direktorijuma: {path}")
                return None
            return full_path
        except Exception as e:
            logger.error(f"Greška pri validaciji putanje {path}: {str(e)}")
            return None

    def _cleanup_old_versions(self, backup_subdir: Path, filename_prefix: str):
        """Održava samo max_backups najnovijih verzija."""
        try:
            # Traži fajlove koji počinju sa imenom originalnog fajla + "_"
            backups = sorted(backup_subdir.glob(f"{filename_prefix}_*.bak"), key=os.path.getmtime)
            
            while len(backups) > self.max_backups:
                oldest = backups.pop(0)
                os.remove(oldest)
                logger.info(f"Obrisan stari backup: {oldest.name}")
        except Exception as e:
            logger.error(f"Greška pri čišćenju starih verzija: {str(e)}")

    def create_backup(self, file_path: str) -> Optional[str]:
        """
        Kreira backup fajla pre izmene.
        Vraća putanju do backup fajla ili None ako fajl ne postoji.
        """
        full_path = self._safe_path(file_path)
        if not full_path or not full_path.exists() or not full_path.is_file():
            return None

        timestamp = int(time.time())
        rel_path = full_path.relative_to(self.base_dir)
        backup_subdir = self.history_dir / rel_path.parent
        backup_subdir.mkdir(parents=True, exist_ok=True)

        # Koristimo "_" kao separator za bolju kompatibilnost
        backup_filename = f"{rel_path.name}_{timestamp}.bak"
        backup_path = backup_subdir / backup_filename

        try:
            shutil.copy2(full_path, backup_path)
            logger.info(f"Backup kreiran: {backup_path}")
            
            # Očisti stare verzije
            self._cleanup_old_versions(backup_subdir, rel_path.name)
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"Greška pri kreiranju backup-a: {str(e)}")
            return None

    def get_history(self, file_path: str) -> List[Dict[str, str]]:
        """Vraća listu dostupnih verzija za dati fajl."""
        full_path = self._safe_path(file_path)
        if not full_path:
            return []
            
        rel_path = full_path.relative_to(self.base_dir)
        backup_subdir = self.history_dir / rel_path.parent
        if not backup_subdir.exists():
            return []

        backups = []
        prefix = rel_path.name + "_"
        
        for backup_file in backup_subdir.glob(f"{prefix}*.bak"):
            try:
                # Format: filename_timestamp.bak
                # Izdvajamo timestamp sa kraja (pre .bak, posle zadnjeg underscore-a)
                name_without_ext = backup_file.name[:-4] # skini .bak
                timestamp_str = name_without_ext.split('_')[-1]
                
                if not timestamp_str.isdigit():
                    continue
                    
                timestamp = int(timestamp_str)
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                backups.append({
                    "version_id": str(timestamp),
                    "timestamp": timestamp,
                    "date": date_str,
                    "path": str(backup_file),
                    "filename": backup_file.name
                })
            except Exception as e:
                logger.warning(f"Greška pri parsiranju backup fajla {backup_file.name}: {e}")
                continue
                
        # Sortiraj od najnovijeg ka najstarijem
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

    def restore_version(self, file_path: str, version_id: str) -> bool:
        """Vraća fajl na određenu verziju."""
        full_path = self._safe_path(file_path)
        if not full_path:
            return False
            
        rel_path = full_path.relative_to(self.base_dir)
        backup_subdir = self.history_dir / rel_path.parent
        
        # Rekonstruišemo ime backup fajla sa novim formatom
        backup_filename = f"{rel_path.name}_{version_id}.bak"
        backup_path = backup_subdir / backup_filename
        
        if not backup_path.exists():
            logger.error(f"Backup verzija {version_id} ne postoji: {backup_path}")
            return False

        try:
            # Pre restore-a, napravimo backup trenutnog stanja (Snapshot pre Undo-a)
            self.create_backup(str(rel_path))
            
            shutil.copy2(backup_path, full_path)
            logger.info(f"Fajl {file_path} vraćen na verziju {version_id}")
            return True
        except Exception as e:
            logger.error(f"Greška pri vraćanju verzije: {str(e)}")
            return False