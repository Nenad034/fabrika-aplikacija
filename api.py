from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import os

from core.orchestrator import SecureOrchestrator
from core.sentinel import SecuritySentinel

app = FastAPI(title="AI Factory API", version="3.0")

# EN: Enable CORS for frontend communication
# SR: Omogući CORS za komunikaciju sa frontendom
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Orchestrator
orchestrator = SecureOrchestrator()

class GenerateRequest(BaseModel):
    prompt: str
    filename: str

class StatusResponse(BaseModel):
    total_tokens: int
    project_dir: str
    model: str
    files: List[str]

@app.get("/status", response_model=StatusResponse)
async def get_status():
    project_dir = str(orchestrator.file_manager.BASE_DIR)
    files = [str(f.relative_to(orchestrator.file_manager.BASE_DIR)) 
             for f in orchestrator.file_manager.BASE_DIR.rglob('*') 
             if f.is_file() and not '.git' in str(f) and not 'node_modules' in str(f)]
    
    return StatusResponse(
        total_tokens=orchestrator.get_token_usage(),
        project_dir=project_dir,
        model=orchestrator.model,
        files=files
    )

@app.get("/read-file")
async def read_file(path: str):
    try:
        content = orchestrator.file_manager.safe_read(path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/save-file")
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

@app.get("/models")
async def get_models():
    # SR: Lista popularnih modela podržanih preko litellm
    return {
        "models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast & Cheap)"},
            {"id": "gpt-4o", "name": "GPT-4o (Most Powerful)"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"}
        ]
    }

@app.post("/set-model")
async def set_model(model_id: str):
    orchestrator.model = model_id
    print(f"[Orchestrator] Model promenjen na: {model_id}")
    return {"success": True, "current_model": model_id}

@app.post("/set-project-dir")
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

@app.get("/pick-dir")
async def pick_dir():
    import subprocess
    try:
        cmd = '[System.Reflection.Assembly]::LoadWithPartialName("System.windows.forms") | Out-Null; $objForm = New-Object System.Windows.Forms.FolderBrowserDialog; $objForm.Description = "Odaberi radni folder projekta"; $result = $objForm.ShowDialog(); if ($result -eq "OK") { Write-Host $objForm.SelectedPath }'
        proc = subprocess.Popen(['powershell', '-Command', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(timeout=60)
        path = stdout.strip()
        if path:
            return await set_project_dir(path)
        return {"success": False, "message": "Otkazano"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.get("/pick-file")
async def pick_file():
    import subprocess
    try:
        cmd = '[System.Reflection.Assembly]::LoadWithPartialName("System.windows.forms") | Out-Null; $objForm = New-Object System.Windows.Forms.OpenFileDialog; $objForm.Filter = "Svi fajlovi (*.*)|*.*"; $result = $objForm.ShowDialog(); if ($result -eq "OK") { Write-Host $objForm.FileName }'
        proc = subprocess.Popen(['powershell', '-Command', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(timeout=60)
        path = stdout.strip()
        if path:
            return {"success": True, "path": path}
        return {"success": False, "message": "Otkazano"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

class GenerateRequest(BaseModel):
    prompt: str
    filename: str
    attachments: Optional[List[Dict[str, Any]]] = None

@app.post("/generate")
async def generate_code(req: GenerateRequest):
    try:
        result = orchestrator.generate_and_validate_code(req.prompt, req.filename, req.attachments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
