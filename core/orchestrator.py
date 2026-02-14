"""
Secure Orchestrator - Mozak AI Fabrike sa ugrađenom bezbednosnom validacijom.
Koordinira LLM pozive, validaciju koda i bezbedno izvršavanje.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import litellm
import json
import asyncio

# Set debug before other operations if needed
litellm.set_debug = True

from core.sentinel import SecuritySentinel, SecurityThreat
from tools.file_manager import FileManager, SecurityError
from tools.history_manager import HistoryManager
from core.agent_manager import AgentManager, Agent
from tools.package_manager import PackageManager
from tools.git_manager import GitManager
from tools.supabase_manager import SupabaseManager

# Učitaj environment varijable
load_dotenv()

# Eksplicitno postavi Gemini API ključ i konfiguraciju
google_api_key = os.getenv('GOOGLE_API_KEY')
if google_api_key:
    os.environ['GEMINI_API_KEY'] = google_api_key
    os.environ['GOOGLE_API_KEY'] = google_api_key
    
    # Konfiguracija litellm za bolju Gemini stabilnost
    litellm.drop_params = True
    print(f"[Environment] Gemini/Google konfiguracija učitana")


class SecureOrchestrator:
    """
    Glavni orkestrator koji upravlja celim procesom generisanja koda.
    Sada podržava Multi-Agent sistem.
    """
    
    def __init__(self, project_dir: Optional[str] = None, max_retries: int = 3):
        """
        Inicijalizuje Secure Orchestrator.
        """
        self.file_manager = FileManager(project_dir)
        self.sentinel = SecuritySentinel()
        self.history_manager = HistoryManager(self.file_manager.BASE_DIR)
        self.agent_manager = AgentManager(self.file_manager.BASE_DIR)
        self.package_manager = PackageManager(str(self.file_manager.BASE_DIR))
        self.git_manager = GitManager(str(self.file_manager.BASE_DIR))
        self.supabase_manager = SupabaseManager()
        self.max_retries = max_retries
        self.total_tokens_used = 0
        
        # Podrazumevani model (može se promeniti)
        self.model = os.getenv('DEFAULT_LLM_MODEL', 'gemini/gemini-3-flash-preview')
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        print(f"[Orchestrator] Inicijalizovan sa modelom: {self.model}")
        print(f"[Orchestrator] Radni direktorijum: {self.file_manager.BASE_DIR}")
        print(f"[Orchestrator] Učitano {len(self.agent_manager.agents)} agenata.")
    
    async def async_stream_code_generation(self, prompt, filename, attachments=None, agent_ids=None, model=None, mode="Planning"):
        """
        Async generator koji podržava paralelno izvršavanje više agenata ili direktan model.
        """
        # 1. Priprema konteksta
        is_global = not filename or filename in ["N/A", "null", "undefined", "General"]
        
        ctx_header = f"Mod: {mode}\n"
        if is_global:
            ctx_header += "Cilj: GLOBALNI PREGLED PROJEKTA (Nije selektovan nijedan fajl)\n"
            global_ctx = self._gather_project_context()
            ctx_header += f"\n{global_ctx}\n"
        else:
            ctx_header += f"Ciljani fajl: {filename}\n"

        user_content = [{"type": "text", "text": f"{ctx_header}\n\nUPIT KORISNIKA: {prompt}"}]
        
        if attachments:
            for att in attachments:
                if att['type'] == 'image' and att['data'].startswith('data:image'):
                    user_content.append({"type": "image_url", "image_url": {"url": att['data']}})
                elif att['type'] == 'file':
                    file_ctx = f"\n\n--- KONTEKST DODATNOG FAJLA: {att['name']} ---\n{att['data']}\n--- KRAJ ---\n"
                    user_content[0]["text"] += file_ctx

        # 2. Određivanje agenata (ili direktnog modela)
        agents_to_use = []
        if agent_ids:
            agents_to_use = [a for a in self.agent_manager.agents if a.id in agent_ids]
        
        if not agents_to_use and model:
            # Ako nema specifičnih agenata, koristimo direktno model
            agents_to_use = [Agent(name="AI Agent", role=f"Expert Developer focus on {mode}", model=model, id="default")]
        
        if not agents_to_use:
            # Fallback na default agenta
            agents_to_use = [self.agent_manager.agents[0]] if self.agent_manager.agents else [Agent(name="AI Agent", role="Expert Developer", model=self.model, id="default")]
            
        queue = asyncio.Queue()

        async def produce(agent: Agent):
            try:
                system_prompt = agent.role
                if is_global:
                    system_prompt += "\nAnaliziraj ceo projekat na osnovu priložene strukture i fajlova. Daj arhitektonski pregled ili odgovori na opšta pitanja o codebase-u."
                
                system_prompt += "\nVAŽNO: Na kraju svakog odgovora koji sadrži predloge ili analizu, obavezno navedi 'SUMARNA LISTA ZADATAKA' sa stavkama (To-Do) šta treba uraditi dalje."
                system_prompt += "\n\nDOSTUPNI ALATI:\n- Instalacija paketa: '/install/python' ili '/install/node'.\n- Git Operacije: '/git/status', '/git/init', '/git/commit', '/git/push'.\n- Supabase: '/supabase/connect', '/supabase/tables'.\n- Primer: 'Za čuvanje promena, preporučujem commit: POST /git/commit {\"message\": \"feat: new feature\"}'"

                messages = [{"role": "system", "content": system_prompt}]
                messages.append({"role": "user", "content": user_content})

                response = await litellm.acompletion(
                    model=agent.model,
                    messages=messages,
                    temperature=0.3,
                    stream=True
                )
                
                full_content_accumulator = ""
                async for chunk in response:
                    if chunk and chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content_accumulator += content
                        await queue.put({
                            "type": "chunk",
                            "agent_id": agent.id,
                            "agent_name": agent.name,
                            "agent_color": agent.color,
                            "content": content
                        })
                
                # Provera koda za preview
                import re
                if "```" in full_content_accumulator:
                    code_match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", full_content_accumulator)
                    if code_match:
                         code = code_match.group(1).strip()
                         is_safe, _ = self.sentinel.scan_code(code)
                         if is_safe:
                             await queue.put({
                                 "type": "preview",
                                 "agent_id": agent.id,
                                 "code": code,
                                 "filename": filename if not is_global else "generated_suggestion.py",
                                 "explanation": full_content_accumulator.replace(code_match.group(0), "").strip()
                             })

            except Exception as e:
                print(f"Agent {agent.name} error: {e}")
                await queue.put({"type": "error", "agent_id": agent.id, "content": str(e)})
            finally:
                await queue.put(None)

        # Pokreni taskove
        for agent in agents_to_use:
            asyncio.create_task(produce(agent))
            
        # Consumer petlja
        finished_agents = 0
        while finished_agents < len(agents_to_use):
            item = await queue.get()
            if item is None:
                finished_agents += 1
                continue
            yield json.dumps(item) + "\n"
        
        # Kraj
        yield json.dumps({"type": "done"}) + "\n"

    def _gather_project_context(self) -> str:
        """Sakuplja globalni kontekst celog projekta."""
        try:
            files = self.file_manager.list_files(max_depth=3)
            # Normalizujemo putanje
            structure = "\n".join([f.replace("\\", "/") for f in files])
            
            context = f"STRUKTURA PROJEKTA (Prva 3 nivoa):\n{structure}\n\n"
            
            # Ključni fajlovi za čitanje (provera u root-u i podfolderima)
            key_files = ["README.md", "requirements.txt", "api.py", "ui/src/App.jsx", "ui/package.json"]
            for kf in key_files:
                try:
                    content = self.file_manager.safe_read(kf)
                    context += f"--- SADRŽAJ KLJUČNOG FAJLA: {kf} ---\n{content[:3000]}\n\n"
                except Exception:
                    # Pokušaj da nađeš fajl ako je putanja drugačija
                    base_name = kf.split('/')[-1]
                    for f in files:
                        if f.endswith(base_name) and base_name in ["App.jsx", "package.json"]:
                             try:
                                 content = self.file_manager.safe_read(f)
                                 context += f"--- SADRŽAJ KLJUČNOG FAJLA (Pronađen): {f} ---\n{content[:3000]}\n\n"
                                 break
                             except: continue
            return context
        except Exception as e:
            return f"Greška pri sakupljanju konteksta: {e}"

    def generate_and_validate_code(self, prompt: str, filename: str, 
                                  attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generiše kod pomoću LLM-a (sinhrono/single-shot) i validira ga.
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
            
            # Slična logika kao async za globalni kontekst
            is_global = not filename or filename in ["N/A", "null", "undefined", "General"]
            
            ctx = ""
            if is_global:
                ctx = self._gather_project_context()
                
            full_prompt = f"{ctx}\n\nCiljani fajl: {filename}\nZahtev: {prompt}"
            
            try:
                generated_code, tokens, explanation = self._call_llm(full_prompt, attachments)
                result['tokens_used'] += tokens
                self.total_tokens_used += tokens
                result['message'] = explanation
            except Exception as e:
                result['message'] = f"Greška pri pozivu LLM-a: {str(e)}"
                print(f"[Orchestrator] ✗ {result['message']}")
                continue
            
            if not generated_code:
                result['success'] = True
                result['message'] = explanation
                return result

            is_safe, threats = self.sentinel.scan_code(generated_code)
            result['threats'] = threats
            
            if is_safe:
                result['success'] = True
                result['code'] = generated_code
                result['preview'] = True
                print(f"[Orchestrator] ✋ Prikazujem izmene za {filename} (Čeka odobrenje)")
                return result
            else:
                print(f"[Orchestrator] ✗ Kod sadrži bezbednosne pretnje!")
                if attempt < self.max_retries:
                    prompt = self._create_fix_prompt(prompt, generated_code, threats)
        
        result['message'] = f'Kod nije mogao biti generisan bezbedno nakon {self.max_retries} pokušaja'
        return result

    def manual_save(self, filename: str, content: str) -> Dict[str, Any]:
        """
        Ručno čuva fajl nakon odobrenja korisnika.
        """
        try:
            is_safe, threats = self.sentinel.scan_code(content)
            if not is_safe:
                return {'success': False, 'message': 'Bezbednosna provera nije prošla!', 'threats': threats}

            backup_path = self.history_manager.create_backup(filename)
            self.file_manager.safe_write(filename, content)
            
            msg = f"Fajl {filename} uspešno sačuvan."
            if backup_path:
                msg += f" (Backup: {os.path.basename(backup_path)})"
                
            print(f"[Orchestrator] ✓ {msg}")
            return {'success': True, 'message': msg, 'backup': backup_path}
        except Exception as e:
            err_msg = f"Greška pri ručnom čuvanju: {str(e)}"
            print(f"[Orchestrator] ✗ {err_msg}")
            return {'success': False, 'message': err_msg}
    
    def _call_llm(self, prompt: str, attachments: Optional[List[Dict[str, Any]]] = None) -> tuple[str, int, str]:
        """
        Poziva LLM (synchronous) - koristi se za generate_and_validate_code.
        """
        messages = [
            {
                "role": "system", 
                "content": """Ti si AI Agent koji pomaže u programiranju. 
                Pravila:
                1. Ako korisnik traži kod, generiši ga unutar ``` blokova.
                2. UVEK prvo daj kratko objašnjenje na srpskom jeziku pre koda.
                3. Ako je pitanje opšte prirode, odgovori tekstualno.
                4. Budi ljubazan i strukturiran."""
            }
        ]
        
        user_content = [{"type": "text", "text": prompt}]
        
        if attachments:
            for att in attachments:
                if att['type'] == 'image' and att['data'].startswith('data:image'):
                    user_content.append({"type": "image_url", "image_url": {"url": att['data']}})
                elif att['type'] == 'file':
                    file_context = f"\n\n--- KONTEKST FAJLA: {att['name']} ---\n{att['data']}\n--- KRAJ KONTEKSTA ---\n"
                    user_content[0]["text"] += file_context
        
        messages.append({"role": "user", "content": user_content})
        
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        code = ""
        explanation = content
        
        if "```" in content:
            import re
            code_match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", content)
            if code_match:
                code = code_match.group(1).strip()
                explanation = content.replace(code_match.group(0), "").strip()
        
        return code, tokens, explanation

    def _create_fix_prompt(self, original_prompt: str, unsafe_code: str, threats: List[SecurityThreat]) -> str:
        threat_descriptions = "\n".join([f"- Linija {t.line_number}: {t.description} ({t.category})" for t in threats if t.severity == 'CRITICAL'])
        return f"""
ORIGINALNI ZAHTEV:
{original_prompt}

GENERISANI KOD SADRŽI BEZBEDNOSNE RANJIVOSTI:
{threat_descriptions}

INSTRUKCIJE ZA PREPRAVKU:
1. Ukloni sve eval(), exec(), compile() pozive
2. Koristi parametrizovane SQL upite
3. Generiši ISPRAVAN i BEZBEDAN kod.
"""
    
    def get_token_usage(self) -> int:
        return self.total_tokens_used
