import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import {
  Files,
  Search,
  Settings,
  Play,
  Save,
  Terminal as TerminalIcon,
  Shield,
  Activity,
  ChevronRight,
  FileCode,
  AlertCircle,
  X,
  Plus,
  Zap,
  Cpu,
  FolderOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8000';

function App() {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [leftSidebarVisible, setLeftSidebarVisible] = useState(true);
  const [rightSidebarVisible, setRightSidebarVisible] = useState(true);
  const [loading, setLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [newFileName, setNewFileName] = useState('generated/new_script.py');

  // Resizing state
  const [leftWidth, setLeftWidth] = useState(260);
  const [rightWidth, setRightWidth] = useState(512);
  const [bottomHeight, setBottomHeight] = useState(160);

  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const [isResizingBottom, setIsResizingBottom] = useState(false);

  const startResizingLeft = () => setIsResizingLeft(true);
  const startResizingRight = () => setIsResizingRight(true);
  const startResizingBottom = () => setIsResizingBottom(true);

  const [theme, setTheme] = useState('dark'); // 'dark', 'navy', 'tokyo'
  const [messages, setMessages] = useState([
    { id: 1, text: "Dobrodošli! Ja sam vaš AI Agent. Kako vam mogu pomoći danas?", type: 'ai' }
  ]);

  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchStatus();
    fetchModels();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => {
    const themes = ['dark', 'navy', 'tokyo'];
    const next = themes[(themes.indexOf(theme) + 1) % themes.length];
    setTheme(next);
  };

  const getMonacoTheme = () => {
    return 'vs-dark'; // Tokyo Night works best with dark editor base
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingLeft) {
        const newWidth = e.clientX - 48; // 48 is activity bar
        if (newWidth > 150 && newWidth < 800) setLeftWidth(newWidth);
      }
      if (isResizingRight) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 200 && newWidth < 1000) setRightWidth(newWidth);
      }
      if (isResizingBottom) {
        const newHeight = window.innerHeight - e.clientY;
        if (newHeight > 50 && newHeight < 600) setBottomHeight(newHeight);
      }
    };
    const stopResizing = () => {
      setIsResizingLeft(false);
      setIsResizingRight(false);
      setIsResizingBottom(false);
    };
    if (isResizingLeft || isResizingRight || isResizingBottom) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', stopResizing);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [isResizingLeft, isResizingRight, isResizingBottom]);

  const fetchModels = async () => {
    try {
      const res = await axios.get(`${API_BASE}/models`);
      setAvailableModels(res.data.models);
    } catch (err) {
      console.error('Failed to fetch models');
    }
  };

  const handleModelChange = async (modelId) => {
    try {
      await axios.post(`${API_BASE}/set-model?model_id=${modelId}`);
      addLog(`Model promenjen: ${modelId}`, 'success');
      fetchStatus();
    } catch (err) {
      addLog(`Greška pri promeni modela`, 'error');
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/status`);
      setStatus(res.data);
      setFiles(res.data.files);
      if (!currentPath && res.data.project_dir) {
        setCurrentPath(res.data.project_dir);
      }
    } catch (err) {
      console.error('Status Error', err);
    }
  };

  const handleSetPath = async () => {
    if (!currentPath) return;
    try {
      const res = await axios.post(`${API_BASE}/set-project-dir?path=${encodeURIComponent(currentPath)}`);
      if (res.data.success) {
        addLog(`Radni folder: ${res.data.project_dir}`, 'success');
        if (res.data.files) setFiles(res.data.files);
        fetchStatus();
      }
    } catch (err) {
      addLog(`Greška: ${err.response?.data?.detail || err.message}`, 'error');
    }
  };

  const handleBrowse = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pick-dir`);
      if (res.data.success) {
        addLog(` Folder izabran: ${res.data.project_dir}`, "success");
        setCurrentPath(res.data.project_dir);
        if (res.data.files) setFiles(res.data.files);
      }
    } catch (err) {
      addLog("Greška pri otvaranju foldera", "error");
    }
  };

  const handleBrowseFile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pick-file`);
      if (res.data.success && res.data.path) {
        handleFileClick(res.data.path);
      }
    } catch (err) {
      addLog("Greška pri otvaranju fajla", "error");
    }
  };

  const addLog = (msg, type = 'info') => {
    setLogs(prev => [...prev.slice(-49), { id: Date.now(), msg, type, time: new Date().toLocaleTimeString() }]);
  };

  const handleFileClick = async (file) => {
    try {
      const res = await axios.get(`${API_BASE}/read-file?path=${file}`);
      setActiveFile(file);
      setFileContent(res.data.content);
      addLog(`Otvaranje: ${file.split('\\').pop()}`, 'info');
    } catch (err) {
      addLog(`Greška pri čitanju fajla`, 'error');
    }
  };

  const handleSave = async () => {
    if (!activeFile) return;
    try {
      const res = await axios.post(`${API_BASE}/save-file?path=${activeFile}&content=${encodeURIComponent(fileContent)}`);
      if (res.data.success) {
        addLog(`✓ Sačuvano`, 'success');
      } else {
        addLog(`✗ Bezbednosni Sentinel je blokirao upis`, 'warning');
        if (res.data.threats) {
          res.data.threats.forEach(t => addLog(`🚨 ${t.description}`, 'warning'));
        }
      }
    } catch (err) {
      addLog(`Kritična greška pri čuvanju`, 'error');
    }
  };

  const handleGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setLoading(true);
    addLog(`AI Robot: Izvršavam zadatak...`, 'info');
    try {
      const res = await axios.post(`${API_BASE}/generate`, { prompt: aiPrompt, filename: newFileName });
      if (res.data.success) {
        addLog(`✓ Uspešno obavljeno!`, 'success');
        setMessages(prev => [...prev, { id: Date.now(), text: `Zadatak je uspešno izvršen u fajlu: ${newFileName}. Kôd je generisan i osiguran.`, type: 'ai' }]);
        fetchStatus();
        setAiPrompt('');
      } else {
        addLog(`✗ Neuspeh AI Agenta`, 'error');
        setMessages(prev => [...prev, { id: Date.now(), text: "Nažalost, došlo je do greške pri izvršavanju zadatka. Proverite logove.", type: 'ai' }]);
      }
    } catch (err) {
      addLog(`Greška API servisa`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (!aiPrompt.trim()) return;
    const userMsg = { id: Date.now(), text: aiPrompt, type: 'user' };
    setMessages(prev => [...prev, userMsg]);
    handleGenerate();
  };

  return (
    <div className={`flex h-screen bg-vscode-bg text-vscode-text font-sans overflow-hidden theme-${theme}`}>
      {/* Activity Bar */}
      <div className="w-12 bg-vscode-activity flex flex-col items-center py-4 space-y-4 border-r border-vscode-border z-20 shrink-0">
        <div
          className="p-2 cursor-pointer text-vscode-accent hover:text-white transition-transform active:scale-95"
          onClick={toggleTheme}
          title="Promeni temu (Dark / Navy / Tokyo Night)"
        >
          {theme === 'dark' ? <Activity size={24} /> : theme === 'navy' ? <Shield size={24} /> : <Zap size={24} className="text-purple-400" />}
        </div>
        <div className="w-8 h-[1px] bg-white/10" />
        <div
          className={`p-2 cursor-pointer transition-colors ${leftSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => setLeftSidebarVisible(!leftSidebarVisible)}
        >
          <Files size={24} />
        </div>
        <div className="p-2 cursor-not-allowed opacity-20"><Search size={24} /></div>
        <div
          className={`p-2 cursor-pointer transition-colors ${rightSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => setRightSidebarVisible(!rightSidebarVisible)}
        >
          <Shield size={24} />
        </div>
        <div className="flex-grow" />
        <Settings className="p-2 opacity-20" size={24} />
      </div>

      {/* Explorer Sidebar */}
      <AnimatePresence>
        {leftSidebarVisible && (
          <>
            <motion.div
              style={{ width: leftWidth }}
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: leftWidth, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="bg-vscode-sidebar border-r border-vscode-border flex flex-col overflow-hidden relative"
            >
              <div className="p-4 uppercase text-[12px] font-bold tracking-widest text-[#888] flex justify-between items-center bg-black/10">
                <span>Explorer</span>
                <Plus className="cursor-pointer hover:text-white" size={17} onClick={handleBrowseFile} />
              </div>

              <div className="p-3 border-y border-white/5 space-y-2 bg-[#252526]/50">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-gray-500 font-bold uppercase">Radni Folder</span>
                  <button onClick={handleBrowse} className="p-1 hover:bg-white/10 rounded text-vscode-accent"><FolderOpen size={14} /></button>
                </div>
                <input
                  type="text"
                  className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1 text-[12px] focus:outline-none focus:border-vscode-accent/50"
                  value={currentPath}
                  onChange={(e) => setCurrentPath(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSetPath()}
                />
              </div>

              <div className="flex-grow overflow-y-auto custom-scrollbar">
                <div className="px-4 py-2 text-[12px] text-gray-500 font-bold uppercase">Fajlovi Projekta</div>
                {files.length > 0 ? files.map(file => (
                  <div
                    key={file}
                    className={`flex items-center px-4 py-2 cursor-pointer text-[14px] ${activeFile === file ? 'bg-vscode-accent/20 text-blue-400 border-l-2 border-vscode-accent' : 'hover:bg-white/5 text-gray-400'}`}
                    onClick={() => handleFileClick(file)}
                  >
                    <FileCode size={17} className="mr-2" />
                    <span className="truncate">{file.split('\\').pop()}</span>
                  </div>
                )) : <div className="p-4 text-[12px] text-gray-600 italic">Prazan folder</div>}
              </div>
            </motion.div>
            <div
              className="w-1 cursor-col-resize hover:bg-vscode-accent transition-colors bg-white/5 z-30"
              onMouseDown={startResizingLeft}
            />
          </>
        )}
      </AnimatePresence>

      {/* Main Content (Editor + Output) */}
      <div className="flex-grow flex flex-col min-w-0 bg-[#1e1e1e]">
        <div className="h-10 bg-vscode-sidebar border-b border-vscode-border flex items-center px-4 justify-between shrink-0">
          <div className="flex items-center text-[14px] truncate max-w-[70%]">
            {activeFile ? (
              <div className="bg-[#1e1e1e] px-4 py-2 border-t-2 border-vscode-accent flex items-center gap-2">
                <FileCode size={14} className="text-blue-400" />
                <span className="truncate font-medium">{activeFile.split('\\').pop()}</span>
              </div>
            ) : <span className="text-[#555] italic text-[14px]">Otvori bilo koji fajl iz Explorera</span>}
          </div>
          <div className="flex items-center gap-1">
            <button onClick={handleSave} disabled={!activeFile} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white disabled:opacity-20">
              <Save size={16} />
            </button>
            <button onClick={() => setActiveFile(null)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white"><X size={16} /></button>
          </div>
        </div>

        <div className="flex-grow relative overflow-hidden">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme={getMonacoTheme()}
            value={fileContent}
            onChange={setFileContent}
            options={{ fontSize: 16, minimap: { enabled: true }, automaticLayout: true, scrollBeyondLastLine: false }}
          />
        </div>

        {/* Output Resizer */}
        <div
          className="h-1 cursor-row-resize hover:bg-vscode-accent transition-colors bg-white/5 z-30"
          onMouseDown={startResizingBottom}
        />

        {/* Output Panel */}
        <div style={{ height: bottomHeight }} className="bg-vscode-sidebar border-t border-vscode-border flex flex-col shrink-0 min-h-[40px]">
          <div className="flex px-4 bg-[#2c2c2c] border-b border-vscode-border items-center justify-between shrink-0 h-8">
            <div className="text-[12px] font-bold border-b-2 border-vscode-accent flex items-center gap-1 h-full uppercase">
              <TerminalIcon size={14} /> Output Console
            </div>
          </div>
          <div className="flex-grow overflow-y-auto p-4 font-mono text-[12px] space-y-1 bg-[#1e1e1e] custom-scrollbar">
            {logs.map(log => (
              <div key={log.id} className="flex gap-3">
                <span className="text-gray-600 shrink-0">[{log.time}]</span>
                <span className={log.type === 'success' ? 'text-green-400' : log.type === 'error' ? 'text-red-400' : log.type === 'warning' ? 'text-yellow-400' : 'text-gray-300'}>
                  {log.msg}
                </span>
              </div>
            ))}
            {logs.length === 0 && <div className="text-gray-600 italic">Čekam na akciju...</div>}
          </div>
        </div>
      </div>

      {/* AI Agent Sidebar (Right) */}
      <AnimatePresence>
        {rightSidebarVisible && (
          <>
            <div
              className="w-1 cursor-col-resize hover:bg-vscode-accent transition-colors bg-white/5 z-30"
              onMouseDown={startResizingRight}
            />
            <motion.div
              style={{ width: rightWidth }}
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: rightWidth, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="bg-vscode-sidebar border-l border-vscode-border flex flex-col overflow-hidden bg-[#252526]"
            >
              <div className="p-4 flex items-center justify-between border-b border-white/5 bg-[#2d2d2d] shrink-0">
                <span className="text-[12px] font-bold uppercase tracking-widest text-vscode-accent flex items-center gap-2">
                  <Shield size={16} /> AI Programming Agent
                </span>
                <X size={16} className="cursor-pointer hover:text-white text-gray-500" onClick={() => setRightSidebarVisible(false)} />
              </div>

              <div className="p-4 flex-grow overflow-y-auto custom-scrollbar flex flex-col space-y-4">
                {/* Chat History View */}
                <div className="flex-grow space-y-3 mb-4">
                  {messages.map(msg => (
                    <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] p-3 rounded-xl text-[13px] leading-relaxed shadow-sm ${msg.type === 'user'
                        ? 'bg-vscode-accent text-white rounded-tr-none'
                        : 'bg-black/20 border border-white/5 text-vscode-text rounded-tl-none'
                        }`}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                <div className="space-y-4 mt-auto border-t border-white/5 pt-4">
                  <div className="space-y-1">
                    <label className="text-[11px] text-gray-400 font-bold uppercase">LLM Brain Selection</label>
                    <select
                      className="w-full bg-vscode-input border border-white/10 rounded px-2 py-2 text-[14px] focus:outline-none focus:border-vscode-accent cursor-pointer text-vscode-text"
                      value={status?.model || ''}
                      onChange={(e) => handleModelChange(e.target.value)}
                    >
                      {availableModels.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-gray-400 font-bold uppercase">Poruka za Agenta</label>
                    <textarea
                      className="w-full bg-vscode-input border border-white/10 rounded p-3 text-[14px] h-32 focus:outline-none focus:border-vscode-accent resize-none placeholder:text-gray-600 text-vscode-text"
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Pitajte agenta bilo šta..."
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendMessage())}
                    />
                  </div>

                  <div className="flex gap-2">
                    <div className="flex-grow space-y-1">
                      <label className="text-[11px] text-gray-400 font-bold uppercase shrink-0">Ciljni Fajl</label>
                      <input
                        type="text"
                        className="w-full bg-vscode-input border border-white/10 rounded px-3 py-2 text-[14px] focus:outline-none focus:border-vscode-accent text-vscode-text"
                        value={newFileName}
                        onChange={(e) => setNewFileName(e.target.value)}
                      />
                    </div>
                    <button
                      className="mt-6 bg-vscode-accent hover:bg-blue-600 text-white p-3 rounded-md font-bold shadow-lg transition-all active:scale-95 disabled:opacity-50 shrink-0"
                      onClick={handleSendMessage}
                      disabled={loading || !aiPrompt}
                    >
                      {loading ? <Cpu className="animate-spin" size={20} /> : <Zap size={20} fill="white" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-black/30 rounded border border-white/5 space-y-2">
                  <div className="flex justify-between text-[12px] text-gray-500 uppercase">
                    <span>Usage Tokens:</span>
                    <span className="text-vscode-accent font-bold">{status?.total_tokens || 0}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[12px] text-green-500/80 font-bold uppercase tracking-tighter">
                    <Shield size={12} /> Protected by Security Sentinel
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
