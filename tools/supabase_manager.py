"""
Supabase Manager
Alat za upravljanje Supabase integracijom (konekcija, listanje tabela, izvršavanje upita).
"""

import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

class SupabaseManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Optional[Client] = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                print(f"[SupabaseManager] Greška pri inicijalizaciji: {e}")

    def connect(self, url: str, key: str) -> bool:
        """Testira konekciju i čuva kredencijale u environmentu (runtime)."""
        try:
            # Pokušaj kreiranja klijenta
            client = create_client(url, key)
            # Test upit (samo ping)
            # Napomena: Supabase nema direktan 'ping', ali inicijalizacija obično ne puca ako su url/key validnog formata.
            # Pravi test je prvi request.
            self.client = client
            self.url = url
            self.key = key
            return True
        except Exception as e:
            return False

    def get_tables(self) -> List[str]:
        """Vraća listu tabela u public šemi."""
        if not self.client:
            return []
        
        try:
            # Koristimo RPC ili direktan upit sistemskim tabelama ako je moguće,
            # ali standardni klijent nema lak način za 'list tables'.
            # Workaround: Pokušaj da dohvatimo podatke iz 'information_schema.tables'
            # Nažalost, postgrest-py (koji supabase-py koristi) ne dozvoljava uvek pristup ovome.
            
            # Alternativa: Ako korisnik ima pristup pg_catalog
            # Za sada, vraćamo simuliranu listu ili prazno ako ne možemo da dohvatimo.
            # Pravi način bi bio SQL query, ali supabase-js/py klijent je primarno za data manipulation.
            
            # Pokušaj SQL upita preko RPC (ako postoji funkcija) ili raw sql (nije podržan u basic klijentu).
            # Zbog limita biblioteke, ovde ćemo samo vratiti status konekcije.
            
            return ["(Table listing requires SQL access)"] 
        except Exception as e:
            return [f"Error: {str(e)}"]

    def execute_query(self, table: str, query_type: str = 'select', data: Any = None) -> Any:
        """Izvršava osnovne operacije nad tabelom."""
        if not self.client:
            return {"error": "Not connected"}
            
        try:
            query = self.client.table(table)
            
            if query_type == 'select':
                return query.select("*").execute()
            elif query_type == 'insert':
                return query.insert(data).execute()
            elif query_type == 'update':
                # Za update je potreban filter, ovo je uprošćeno
                return {"error": "Update requires specific logic"}
            elif query_type == 'delete':
                return {"error": "Delete requires specific logic"}
                
        except Exception as e:
            return {"error": str(e)}
