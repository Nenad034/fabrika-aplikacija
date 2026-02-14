"""
Dependency Detector
Automatski detektuje nedostajuće Python i Node.js zavisnosti u projektu.
"""

import ast
import os
import json
from pathlib import Path
from typing import List, Dict, Set
import re

class DependencyDetector:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        
        # Standardne biblioteke koje ne treba instalirati
        self.python_stdlib = {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'math', 'random',
            'collections', 'itertools', 'functools', 'pathlib', 'subprocess',
            'typing', 'asyncio', 'threading', 'multiprocessing', 'logging',
            'unittest', 'pytest', 'argparse', 'configparser', 'io', 'csv',
            'xml', 'html', 'http', 'urllib', 'email', 'base64', 'hashlib',
            'pickle', 'shelve', 'sqlite3', 'socket', 'ssl', 'abc', 'enum'
        }
        
        # Node.js built-in moduli
        self.node_builtins = {
            'fs', 'path', 'http', 'https', 'url', 'querystring', 'crypto',
            'stream', 'events', 'util', 'os', 'process', 'child_process',
            'cluster', 'net', 'dgram', 'dns', 'tls', 'readline', 'zlib',
            'buffer', 'string_decoder', 'timers', 'console', 'assert'
        }
    
    def detect_python_imports(self, file_path: Path) -> Set[str]:
        """
        Detektuje sve import statement-e iz Python fajla.
        
        Returns:
            Set imena paketa (top-level)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Uzmi samo top-level paket (npr. 'requests' iz 'requests.auth')
                        package = alias.name.split('.')[0]
                        imports.add(package)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        package = node.module.split('.')[0]
                        imports.add(package)
            
            return imports
            
        except Exception as e:
            print(f"[DependencyDetector] Greška pri parsiranju {file_path}: {e}")
            return set()
    
    def detect_node_imports(self, file_path: Path) -> Set[str]:
        """
        Detektuje sve import/require statement-e iz JS/JSX fajla.
        
        Returns:
            Set imena paketa
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            imports = set()
            
            # Regex za ES6 import
            # import ... from 'package'
            # import ... from "package"
            import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
            for match in re.finditer(import_pattern, content):
                package = match.group(1)
                # Ignoriši relativne putanje
                if not package.startswith('.') and not package.startswith('/'):
                    # Uzmi samo ime paketa (npr. 'react' iz 'react/jsx-runtime')
                    package_name = package.split('/')[0]
                    # Ignoriši @scope pakete sa scope-om
                    if package.startswith('@'):
                        package_name = '/'.join(package.split('/')[:2])
                    imports.add(package_name)
            
            # Regex za CommonJS require
            # require('package')
            # require("package")
            require_pattern = r"require\(['\"]([^'\"]+)['\"]\)"
            for match in re.finditer(require_pattern, content):
                package = match.group(1)
                if not package.startswith('.') and not package.startswith('/'):
                    package_name = package.split('/')[0]
                    if package.startswith('@'):
                        package_name = '/'.join(package.split('/')[:2])
                    imports.add(package_name)
            
            return imports
            
        except Exception as e:
            print(f"[DependencyDetector] Greška pri parsiranju {file_path}: {e}")
            return set()
    
    def scan_project_python(self) -> Set[str]:
        """
        Skenira sve Python fajlove u projektu.
        
        Returns:
            Set svih detektovanih paketa
        """
        all_imports = set()
        
        for py_file in self.project_root.rglob('*.py'):
            # Ignoriši virtuelne okruženja i cache foldere
            if any(part in py_file.parts for part in ['venv', 'env', '__pycache__', '.venv', 'node_modules']):
                continue
            
            imports = self.detect_python_imports(py_file)
            all_imports.update(imports)
        
        # Filtriraj standardne biblioteke
        external_packages = all_imports - self.python_stdlib
        
        return external_packages
    
    def scan_project_node(self) -> Set[str]:
        """
        Skenira sve JS/JSX fajlove u projektu.
        
        Returns:
            Set svih detektovanih paketa
        """
        all_imports = set()
        
        for ext in ['*.js', '*.jsx', '*.ts', '*.tsx']:
            for js_file in self.project_root.rglob(ext):
                # Ignoriši node_modules i build foldere
                if any(part in js_file.parts for part in ['node_modules', 'dist', 'build', '.next']):
                    continue
                
                imports = self.detect_node_imports(js_file)
                all_imports.update(imports)
        
        # Filtriraj built-in module
        external_packages = all_imports - self.node_builtins
        
        return external_packages
    
    def get_installed_python_packages(self) -> Set[str]:
        """
        Vraća set instaliranih Python paketa.
        """
        from tools.package_manager import PackageManager
        pm = PackageManager(str(self.project_root))
        
        packages = pm.list_python_packages()
        return {pkg['name'].lower() for pkg in packages}
    
    def get_installed_node_packages(self) -> Set[str]:
        """
        Vraća set instaliranih Node.js paketa iz package.json.
        """
        package_json = self.project_root / 'package.json'
        
        if not package_json.exists():
            return set()
        
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            deps = set(data.get('dependencies', {}).keys())
            dev_deps = set(data.get('devDependencies', {}).keys())
            
            return deps | dev_deps
            
        except Exception as e:
            print(f"[DependencyDetector] Greška pri čitanju package.json: {e}")
            return set()
    
    def detect_missing(self) -> Dict[str, List[str]]:
        """
        Detektuje nedostajuće zavisnosti.
        
        Returns:
            Dict sa 'python' i 'node' listama nedostajućih paketa
        """
        # Python
        used_python = self.scan_project_python()
        installed_python = self.get_installed_python_packages()
        missing_python = sorted(list(used_python - installed_python))
        
        # Node.js
        used_node = self.scan_project_node()
        installed_node = self.get_installed_node_packages()
        missing_node = sorted(list(used_node - installed_node))
        
        return {
            'python': missing_python,
            'node': missing_node
        }
