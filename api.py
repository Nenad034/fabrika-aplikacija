from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

# Učitaj environment pre svega
load_dotenv()

from core.orchestrator import SecureOrchestrator
from core.sentinel import SecuritySentinel
from tools.package_manager import PackageManager
from tools.dependency_detector import DependencyDetector
from tools.git_manager import GitManager
from tools.supabase_manager import SupabaseManager

app = FastAPI(title="AI Factory API", version="3.0")

# SR: Bezbedna CORS konfiguracija - dozvoljavamo samo lokalne portove
# Uključujemo i localhost i 127.0.0.1 jer browser može koristiti bilo koji
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Token zaštita
API_TOKEN = os.getenv("API_TOKEN")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)):
    if API_TOKEN and api_key != API_TOKEN:
        raise HTTPException(status_code=401, detail="Neautorizovan pristup: Nevažeći API Token")
    return api_key

# Initialize Orchestrator, PackageManager, DependencyDetector, GitManager, and SupabaseManager
orchestrator = SecureOrchestrator()
package_manager = PackageManager(str(orchestrator.file_manager.BASE_DIR))
dependency_detector = DependencyDetector(str(orchestrator.file_manager.BASE_DIR))
git_manager = GitManager(str(orchestrator.file_manager.BASE_DIR))
supabase_manager = SupabaseManager()

class GenerateRequest(BaseModel):
    prompt: str
    filename: str

class StatusResponse(BaseModel):
    total_tokens: int
    project_dir: str
    roots: List[str]
    model: str
    files: List[str]

@app.get("/status", response_model=StatusResponse, dependencies=[Depends(get_api_key)])
async def get_status():
    project_dir = str(orchestrator.file_manager.BASE_DIR)
    # SR: Koristimo optimizovanu list_files metodu koja ignoriše node_modules i sl.
    files = orchestrator.file_manager.list_files(max_depth=2)
    
    return StatusResponse(
        total_tokens=orchestrator.get_token_usage(),
        project_dir=project_dir,
        roots=[str(r) for r in orchestrator.file_manager.roots],
        model=orchestrator.model,
        files=files
    )

@app.get("/read-file", dependencies=[Depends(get_api_key)])
async def read_file(path: str):
    try:
        content = orchestrator.file_manager.safe_read(path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/save-file", dependencies=[Depends(get_api_key)])
async def save_file(path: str, content: str):
    # Proveri kod pre čuvanja
    is_safe, threats = orchestrator.sentinel.scan_code(content)
    if not is_safe:
        return {"success": False, "message": "Bezbednosna provera nije prošla", "threats": threats}
    
    try:
        orchestrator.file_manager.safe_write(path, content)
        return {"success": True, "message": "Fajl uspešno sačuvan"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models", dependencies=[Depends(get_api_key)])
async def get_models():
    # SR: Lista popularnih modela podržanih preko litellm
    return {
        "models": [
            {"id": "gemini/gemini-3-flash-preview", "name": "Gemini 3 Flash (Fast & Cheap)"},
            {"id": "gemini/gemini-3-pro-high-preview", "name": "Gemini 3 Pro High (Ultra Powerful)"},
            {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B (Powerful & Open)"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3 (Coding Specialist)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"}
        ]
    }

@app.post("/set-model", dependencies=[Depends(get_api_key)])
async def set_model(model_id: str):
    orchestrator.model = model_id
    print(f"[Orchestrator] Model promenjen na: {model_id}")
    return {"success": True, "current_model": model_id}

@app.post("/set-project-dir", dependencies=[Depends(get_api_key)])
async def set_project_dir(path: str):
    from tools.file_manager import FileManager
    from pathlib import Path
    try:
        # Normalize and resolve path for Windows stability
        p = Path(path).resolve()
        
        if not p.exists():
            raise HTTPException(status_code=400, detail=f"Putanja ne postoji: {path}")
        
        if not p.is_dir():
            raise HTTPException(status_code=400, detail="Izabrana putanja mora biti folder")
        
        # SR: Bezbednosna provera - spreči skok korenskog foldera na sistemske nivoe bez odobrenja
        # U budućnosti uvesti listu "dozvoljenih" roditeljskih foldera u .env
        
        # Re-initialize FileManager with the NEW base directory
        orchestrator.file_manager = FileManager(str(p))
        print(f"[Orchestrator] Workspace promenjen na: {p}")
        
        # Return the new list of files immediately for UI refresh
        files = orchestrator.file_manager.list_files()
        return {
            "success": True, 
            "project_dir": str(p),
            "files": files
        }
    except Exception as e:
        print(f"[Error] Failed to set project dir: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-project-dir", dependencies=[Depends(get_api_key)])
async def add_project_dir(path: str):
    try:
        if orchestrator.file_manager.add_root(path):
            return {"success": True, "roots": [str(r) for r in orchestrator.file_manager.roots], "files": orchestrator.file_manager.list_files()}
        else:
            return {"success": False, "message": "Nevalidna putanja ili folder ne postoji"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remove-project-dir", dependencies=[Depends(get_api_key)])
async def remove_project_dir(path: str):
    try:
        if orchestrator.file_manager.remove_root(path):
            return {"success": True, "roots": [str(r) for r in orchestrator.file_manager.roots], "files": orchestrator.file_manager.list_files()}
        else:
            return {"success": False, "message": "Neuspešno uklanjanje. Možda je to primarni folder?"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_native_picker_logic():
    import ctypes
    from ctypes import wintypes
    import platform
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def run_picker_thread():
        try:
            if platform.system() != "Windows":
                import subprocess
                import sys
                cmd = [
                    sys.executable, '-c',
                    "import tkinter as tk; from tkinter import filedialog; root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', 1); print(filedialog.askdirectory());"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return res.stdout.strip()

            # SR: Modern Windows IFileOpenDialog implementation (Vista+)
            print("[pick-dir] Pokretanje IFileOpenDialog (Modern)...")
            

            try:
                # GUID Structure
                class GUID(ctypes.Structure):
                    _fields_ = [
                        ("Data1", ctypes.c_ulong),
                        ("Data2", ctypes.c_ushort),
                        ("Data3", ctypes.c_ushort),
                        ("Data4", ctypes.c_ubyte * 8)
                    ]

                # CLSID_FileOpenDialog = {DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}
                CLSID_FileOpenDialog = GUID(0xDC1C5A9C, 0xE88A, 0x4dde, (ctypes.c_ubyte * 8)(0xA5, 0xA1, 0x60, 0xF8, 0x2A, 0x20, 0xAE, 0xF7))
                
                # IID_IFileOpenDialog = {d57c7288-d4ad-4768-be02-9d969532d960}
                IID_IFileOpenDialog = GUID(0xd57c7288, 0xd4ad, 0x4768, (ctypes.c_ubyte * 8)(0xbe, 0x02, 0x9d, 0x96, 0x95, 0x32, 0xd9, 0x60))

                FOS_PICKFOLDERS = 0x20
                FOS_FORCEFILESYSTEM = 0x40
                SIGDN_FILESYSPATH = 0x80058000
                WINFUNCTYPE = ctypes.WINFUNCTYPE
                
                # Structures inlined for brevity (identical to previous)
                class IUnknown(ctypes.Structure):
                    _fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]
                
                Show_Prototype = WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)
                SetOptions_Prototype = WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_ulong)
                GetResult_Prototype = WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(IUnknown)))
                GetDisplayName_Prototype = WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(wintypes.LPWSTR))
                Release_Prototype = WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)

                ole32 = ctypes.windll.ole32
                user32 = ctypes.windll.user32
                ole32.CoInitialize(None)

                pFileDialog = ctypes.POINTER(IUnknown)()
                
                hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FileOpenDialog), None, 1, ctypes.byref(IID_IFileOpenDialog), ctypes.byref(pFileDialog))
                if hr != 0: 
                    print(f"[ModernPicker] CoCreateInstance failed: {hex(hr)}")
                    raise Exception(f"CoCreateInstance failed with hr={hex(hr)}")

                vtbl = pFileDialog.contents.lpVtbl
                SetOptions = SetOptions_Prototype(vtbl[9])
                hr_opt = SetOptions(pFileDialog, FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM)
                if hr_opt != 0: print(f"[ModernPicker] Warning: SetOptions failed: {hex(hr_opt)}")

                Show = Show_Prototype(vtbl[3])
                hwnd = user32.GetForegroundWindow()
                print(f"[ModernPicker] Showing dialog with owner HWND: {hwnd}")
                hr = Show(pFileDialog, hwnd)
                
                print(f"[ModernPicker] Show returned: {hex(hr)}")
                
                path = ""
                if hr == 0:
                    pShellItem = ctypes.POINTER(IUnknown)()
                    GetResult = GetResult_Prototype(vtbl[20])
                    if GetResult(pFileDialog, ctypes.byref(pShellItem)) == 0:
                        item_vtbl = pShellItem.contents.lpVtbl
                        GetDisplayName = GetDisplayName_Prototype(item_vtbl[5])
                        pszName = wintypes.LPWSTR()
                        if GetDisplayName(pShellItem, SIGDN_FILESYSPATH, ctypes.byref(pszName)) == 0 and pszName.value:
                            path = pszName.value
                            ole32.CoTaskMemFree(pszName)
                        else:
                            print("[ModernPicker] Failed to get display name or empty")
                        Release = Release_Prototype(item_vtbl[2])
                        Release(pShellItem)
                    else:
                         print("[ModernPicker] GetResult failed")

                Release = Release_Prototype(vtbl[2])
                Release(pFileDialog)
                ole32.CoUninitialize()
                return path

            except Exception as e:
                print(f"[ModernPicker] Exception: {e}")
                import traceback
                traceback.print_exc()
                return ""
        except Exception as e:
            print(f"[PickerThread] Error: {e}")
            return ""

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, run_picker_thread)

@app.get("/pick-dir", dependencies=[Depends(get_api_key)])
async def pick_dir():
    path = await run_native_picker_logic()
    print(f"[pick-dir] Rezultat: {path}")
    if path:
        return await set_project_dir(path)
    return {"success": False, "message": "Izbor otkazan"}

@app.get("/pick-additional-dir", dependencies=[Depends(get_api_key)])
async def pick_additional_dir():
    path = await run_native_picker_logic()
    if path:
        return await add_project_dir(path) # Assuming add_project_dir exists or similar logic
    return {"success": False, "message": "Izbor otkazan"}


@app.get("/pick-file", dependencies=[Depends(get_api_key)])
async def pick_file():
    import subprocess
    import sys
    try:
        cmd = [sys.executable, '-c', "import tkinter as tk; from tkinter import filedialog; root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', 1); print(filedialog.askopenfilename());"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        path = res.stdout.strip()
        
        if path:
            return {"success": True, "path": path}
        return {"success": False, "message": "Otkazano"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.get("/search", dependencies=[Depends(get_api_key)])
async def search_files(query: str):
    if not query:
        return {"results": []}
    
    results = []
    base_dir = orchestrator.file_manager.BASE_DIR
    
    try:
        for file_path in base_dir.rglob('*'):
            if file_path.is_file() and not any(part in str(file_path) for part in ['.git', 'node_modules', '__pycache__', '.venv']):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                results.append({
                                    "file": str(file_path.relative_to(base_dir)),
                                    "line": i + 1,
                                    "content": line.strip()
                                })
                                if len(results) > 100: # Limit results
                                    return {"results": results}
                except:
                    continue
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateRequest(BaseModel):
    prompt: str
    target_file: str
    attachments: Optional[List[Dict[str, Any]]] = None
    model: Optional[str] = None
    mode: Optional[str] = "Planning"

class AgentRequest(BaseModel):
    name: str
    role: str
    model: str = "gpt-4o-mini"
    color: str = "blue"

@app.get("/agents", dependencies=[Depends(get_api_key)])
async def get_agents():
    return {"agents": [a.dict() for a in orchestrator.agent_manager.agents]}

@app.post("/add-agent", dependencies=[Depends(get_api_key)])
async def add_agent(req: AgentRequest):
    from core.agent_manager import Agent
    new_agent = Agent(**req.dict())
    orchestrator.agent_manager.add_agent(new_agent)
    return {"success": True, "agent": new_agent.dict()}

@app.post("/toggle-agent", dependencies=[Depends(get_api_key)])
async def toggle_agent(agent_id: str, active: bool):
    if orchestrator.agent_manager.update_agent(agent_id, {"is_active": active}):
        return {"success": True}
    return {"success": False, "message": "Agent not found"}

@app.post("/generate", dependencies=[Depends(get_api_key)])
async def generate_code(req: GenerateRequest):
    try:
        result = orchestrator.generate_and_validate_code(req.prompt, req.filename, req.attachments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse

@app.post("/stream-generate", dependencies=[Depends(get_api_key)])
async def stream_generate_code(req: GenerateRequest):
    try:
        return StreamingResponse(
            orchestrator.async_stream_code_generation(
                req.prompt, 
                req.target_file, 
                req.attachments, 
                model=req.model, 
                mode=req.mode
            ),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApplyRequest(BaseModel):
    filename: str
    content: str

@app.post("/apply-changes", dependencies=[Depends(get_api_key)])
async def apply_changes(req: ApplyRequest):
    try:
        result = orchestrator.manual_save(req.filename, req.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Package Installation Endpoints
class InstallRequest(BaseModel):
    package: str
    dev: Optional[bool] = False

@app.post("/install/python", dependencies=[Depends(get_api_key)])
async def install_python_package(req: InstallRequest):
    try:
        success, message = package_manager.install_python(req.package)
        return {"success": success, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/install/node", dependencies=[Depends(get_api_key)])
async def install_node_package(req: InstallRequest):
    try:
        success, message = package_manager.install_node(req.package, req.dev)
        return {"success": success, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/install/check-python", dependencies=[Depends(get_api_key)])
async def check_python_package(package: str):
    try:
        installed, version = package_manager.check_python_package(package)
        return {"installed": installed, "version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/install/check-node", dependencies=[Depends(get_api_key)])
async def check_node_package(package: str):
    try:
        installed, version = package_manager.check_node_package(package)
        return {"installed": installed, "version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/install/list-python", dependencies=[Depends(get_api_key)])
async def list_python_packages():
    try:
        packages = package_manager.list_python_packages()
        return {"packages": packages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/install/detect-missing", dependencies=[Depends(get_api_key)])
async def detect_missing_dependencies():
    try:
        missing = dependency_detector.detect_missing()
        return missing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Git Endpoints
class CommitRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None

@app.get("/git/status", dependencies=[Depends(get_api_key)])
async def git_status():
    try:
        if not git_manager.is_git_initialized():
            return {"initialized": False}
        status = git_manager.status()
        return {"initialized": True, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/init", dependencies=[Depends(get_api_key)])
async def git_init():
    try:
        success, output = git_manager.init()
        return {"success": success, "message": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/commit", dependencies=[Depends(get_api_key)])
async def git_commit(req: CommitRequest):
    try:
        # Prvo dodajemo fajlove (ako nisu specificirani, dodaj sve)
        files_to_add = req.files if req.files else ["."]
        git_manager.add(files_to_add)
        
        # Onda komitujemo
        success, output = git_manager.commit(req.message)
        return {"success": success, "message": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/push", dependencies=[Depends(get_api_key)])
async def git_push():
    try:
        success, output = git_manager.push()
        return {"success": success, "message": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Supabase Endpoints
class SupabaseConnectRequest(BaseModel):
    url: str
    key: str

@app.post("/supabase/connect", dependencies=[Depends(get_api_key)])
async def supabase_connect(req: SupabaseConnectRequest):
    try:
        success = supabase_manager.connect(req.url, req.key)
        if success:
            # Automatski pokušaj dohvatanja tabela nakon konekcije
            tables = supabase_manager.get_tables()
            return {"success": True, "message": "Connected to Supabase", "tables": tables}
        else:
            return {"success": False, "message": "Failed to connect"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/supabase/tables", dependencies=[Depends(get_api_key)])
async def supabase_tables():
    try:
        tables = supabase_manager.get_tables()
        return {"success": True, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # SR: Vraćanje na 0.0.0.0 radi bolje kompatibilnosti tokom dijagnostike
    uvicorn.run(app, host="0.0.0.0", port=8000)
