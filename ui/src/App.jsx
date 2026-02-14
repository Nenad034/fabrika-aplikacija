import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

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
  FolderOpen,
  Paperclip,
  Image as ImageIcon,
  FileText,
  Users, // SR: Icon for Agents
  Bot,
  Check,
  Mic,
  PlusSquare,
  Square,
  ChevronDown,
  Copy, // SR: Added for Copy Chat
  Package, // SR: Added for Package Manager
  Link // SR: Added for Integration Manager
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8000';
const API_TOKEN = 'e74faf31-9dcc-4524-acad-6bbfd374ba38'; // SR: Match with .env

// SR: Configure Axios with Global Interceptor for API Token
axios.interceptors.request.use(config => {
  if (config.url.startsWith(API_BASE)) {
    config.headers['X-API-Key'] = API_TOKEN;
  }
  return config;
}, error => Promise.reject(error));

function App() {
  const [files, setFiles] = useState([]);
  const [openFiles, setOpenFiles] = useState([]); // [{path, content, isDirty}]
  const [activeFile, setActiveFile] = useState(null); // Trenutno aktivna putanja
  const [fileContent, setFileContent] = useState(''); // Samo za Editor, sinhronizovano
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [leftSidebarVisible, setLeftSidebarVisible] = useState(true);
  const [rightSidebarVisible, setRightSidebarVisible] = useState(true);
  const [loading, setLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [showConsole, setShowConsole] = useState(true); // SR: Console visible by default
  const [consolePos, setConsolePos] = useState({ x: window.innerWidth - 650, y: 100 });
  const [consoleSize, setConsoleSize] = useState({ width: 600, height: 400 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isResizing, setIsResizing] = useState(false);

  // Drag logic for Floating Console
  const startDragging = (e) => {
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - consolePos.x,
      y: e.clientY - consolePos.y
    });
  };

  const startResizingConsole = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setConsolePos({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
      if (isResizing) {
        setConsoleSize({
          width: Math.max(300, e.clientX - consolePos.x),
          height: Math.max(200, e.clientY - consolePos.y)
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, consolePos, dragOffset]);
  const [currentPath, setCurrentPath] = useState('');
  const [roots, setRoots] = useState([]);
  const [aiPrompt, setAiPrompt] = useState('');
  const [globalTargetFile, setGlobalTargetFile] = useState('General'); // Globalni target kada nema tabova
  const [leftSidebarMode, setLeftSidebarMode] = useState('explorer'); // 'explorer', 'search'
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Agents & Chat State
  const [chatMode, setChatMode] = useState('Planning'); // 'Planning' ili 'Act'
  const [currentModel, setCurrentModel] = useState('gemini/gemini-3-flash-preview'); // SR: Default model odobren od korisnika

  // SR: Package Manager State
  const [installedPythonPackages, setInstalledPythonPackages] = useState([]);
  const [installedNodePackages, setInstalledNodePackages] = useState([]);
  const [missingPackages, setMissingPackages] = useState({ python: [], node: [] });
  const [packageTab, setPackageTab] = useState('python'); // 'python' | 'node'
  const [packageSearchQuery, setPackageSearchQuery] = useState('');
  const [isInstallingPackage, setIsInstallingPackage] = useState(false);
  const [newPackageName, setNewPackageName] = useState('');
  const [isDevDependency, setIsDevDependency] = useState(false);

  // SR: Integration Manager State
  const [integrationMode, setIntegrationMode] = useState('github'); // 'github' | 'vercel' | 'supabase'
  const [gitStatus, setGitStatus] = useState({ modified: [], staged: [], untracked: [], initialized: false });
  const [commitMessage, setCommitMessage] = useState('');
  const [isPushing, setIsPushing] = useState(false);

  // SR: Supabase State
  const [supabaseUrl, setSupabaseUrl] = useState('');
  const [supabaseKey, setSupabaseKey] = useState('');
  const [supabaseConnected, setSupabaseConnected] = useState(false);
  const [supabaseTables, setSupabaseTables] = useState([]);
  const [isConnectingSupabase, setIsConnectingSupabase] = useState(false);

  const [agents, setAgents] = useState([]); // Zadržavamo za backend kompatibilnost
  const [isChatMaximized, setIsChatMaximized] = useState(false); // SR: Za proširenje na +

  // Resizing state
  const [leftWidth, setLeftWidth] = useState(260);
  const [rightWidth, setRightWidth] = useState(512);
  const [bottomHeight, setBottomHeight] = useState(450);

  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const [isResizingBottom, setIsResizingBottom] = useState(false);

  const startResizingLeft = () => setIsResizingLeft(true);
  const startResizingRight = () => setIsResizingRight(true);
  const startResizingBottom = () => setIsResizingBottom(true);

  // SR: Teme su fiksne, ali poruke su sada podeljene na globalne i per-tab
  const [globalMessages, setGlobalMessages] = useState([
    { id: 1, text: "Dobrodošli! Ovo je globalni kontekst. Kako vam mogu pomoći danas?", type: 'ai' }
  ]);
  const [attachments, setAttachments] = useState([]);
  const fileInputRef = useRef(null);

  // SR: Copy Chat Functionality
  const handleCopyChat = () => {
    const currentMessages = activeFile
      ? (openFiles.find(f => f.path === activeFile)?.messages || [])
      : globalMessages;

    if (currentMessages.length === 0) return;

    const formattedChat = currentMessages.map(msg => {
      const sender = msg.type === 'user' ? 'Korisnik' : 'AI Agent';
      return `### ${sender}\n${msg.text}\n`;
    }).join('\n---\n\n');

    navigator.clipboard.writeText(formattedChat).then(() => {
      addLog("Razgovor kopiran u clipboard!", "success");
    }).catch(err => {
      addLog("Greška pri kopiranju", "error");
    });
  };

  const handleEditorWillMount = (monaco) => {
    // SR: Definicija NAVY Teme za Editor (usklađeno sa novim Teget dizajnom)
    monaco.editor.defineTheme('navy-theme', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: '', foreground: 'ffffff', background: '0a192f' }, // Deepest Navy BG, White Text
        { token: 'comment', foreground: '8892b0', fontStyle: 'italic' }, // Muted Navy
        { token: 'keyword', foreground: '64ffda' }, // Cyan Mint
        { token: 'string', foreground: 'a8d0db' }, // Light Blue
        { token: 'number', foreground: 'f78c6c' }, // Orange accent
      ],
      colors: {
        'editor.background': '#0a192f',
        'editor.foreground': '#ffffff',
        'editorLineNumber.foreground': '#405070',
        'editor.selectionBackground': '#233554',
        'editorCursor.foreground': '#64ffda', // Cyan kursor
      }
    });
  };

  const chatEndRef = useRef(null);

  // ... (scrollToBottom ostaje isti)

  // ... (ostatak handle logika ostaje isti do return-a)

  useEffect(() => {
    fetchStatus();
    fetchAgents(); // SR: Load agents on mount
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await axios.get(`${API_BASE}/agents`);
      if (res.data.agents) setAgents(res.data.agents);
    } catch (err) {
      console.error("Failed to fetch agents", err);
    }
  };

  const toggleAgent = async (agentId, currentStatus) => {
    try {
      await axios.post(`${API_BASE}/toggle-agent?agent_id=${agentId}&active=${!currentStatus}`);
      fetchAgents();
    } catch (err) {
      addLog("Greška pri menjanju statusa agenta", "error");
    }
  };

  const handleCreateAgent = async () => {
    if (!newAgentName || !newAgentRole) return;
    try {
      await axios.post(`${API_BASE}/add-agent`, {
        name: newAgentName,
        role: newAgentRole,
        model: newAgentModel, // SR: Koristi izabrani model umesto hardkodovanog
        color: "blue" // Default color
      });
      setNewAgentName('');
      setNewAgentRole('');
      setNewAgentModel('gemini/gemini-3-flash-preview'); // SR: Reset na default
      setIsAddingAgent(false);
      fetchAgents();
      addLog("Novi agent kreiran!", "success");
    } catch (err) {
      addLog("Greška pri kreiranju agenta", "error");
    }
  };

  // ... (scrollToBottom ostaje isti)
  /*
  <button
    onClick={handleGenerate}
    disabled={loading}
    className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-all shadow-lg
      ${loading 
        ? 'bg-gray-600 cursor-not-allowed opacity-50' 
        : 'bg-[#8b0000] hover:bg-[#a50000] text-white hover:shadow-red-900/20 active:scale-95'
      }`}
  >
    {loading ? (
      <>
        <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
        <span>Radim...</span>
      </>
    ) : (
      <>
        <Zap size={14} className={loading ? "animate-pulse" : ""} />
        <span>Kreni...</span>
      </>
    )}
  </button>
  */

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [globalMessages, openFiles, activeFile]); // SR: Reaguj na promene bilo kog bafere poruka

  useEffect(() => {
    fetchStatus();
    fetchModels();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

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
      if (res.data && res.data.models) {
        setAvailableModels(res.data.models);
      }
    } catch (err) {
      console.error('Failed to fetch models, retrying...');
      setTimeout(fetchModels, 3000); // Retry after 3s if failed
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
      if (res.data.roots) setRoots(res.data.roots);
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
        if (res.data.roots) setRoots(res.data.roots); // Update roots
        fetchStatus();
      }
    } catch (err) {
      addLog("Greška pri otvaranju foldera", "error");
    }
  };

  const handleAddFolder = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pick-additional-dir`);
      if (res.data.success) {
        addLog(`Dodat folder.`, "success");
        if (res.data.roots) setRoots(res.data.roots);
        if (res.data.files) setFiles(res.data.files);
        fetchStatus();
      }
    } catch (err) {
      addLog("Greška pri dodavanju foldera", "error");
    }
  };

  const handleRemoveFolder = async (path) => {
    try {
      const res = await axios.post(`${API_BASE}/remove-project-dir?path=${encodeURIComponent(path)}`);
      if (res.data.success) {
        addLog(`Folder uklonjen iz radnog prostora.`, "info");
        if (res.data.roots) setRoots(res.data.roots);
        if (res.data.files) setFiles(res.data.files);
        fetchStatus();
      } else {
        addLog(res.data.message, "warning");
      }
    } catch (err) {
      addLog("Greška pri uklanjanju foldera", "error");
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

  const handlePickTargetFile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pick-file`);
      if (res.data.success && res.data.path) {
        let path = res.data.path;
        if (currentPath && path.startsWith(currentPath)) {
          path = path.replace(currentPath, '').replace(/^[\\\/]+/, '');
        }

        if (activeFile) {
          setOpenFiles(prev => prev.map(f => f.path === activeFile ? { ...f, targetFile: path } : f));
        } else {
          setGlobalTargetFile(path);
        }

        addLog(`Ciljni fajl: ${path.split(/[\\\/]/).pop()}`, 'success');
      }
    } catch (err) {
      addLog("Greška pri izboru ciljnog fajla", "error");
    }
  };

  const handleSearch = async (val) => {
    setSearchQuery(val);
    if (!val || val.length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const res = await axios.get(`${API_BASE}/search?query=${encodeURIComponent(val)}`);
      setSearchResults(res.data.results);
    } catch (err) {
      console.error("Search failed", err);
    } finally {
      setIsSearching(false);
    }
  };

  // SR: Package Management Functions
  const fetchInstalledPackages = async () => {
    try {
      const res = await axios.get(`${API_BASE}/install/list-python`);
      setInstalledPythonPackages(res.data.packages || []);
    } catch (err) {
      addLog("Greška pri učitavanju instaliranih paketa", "error");
    }
  };

  const detectMissingPackages = async () => {
    try {
      addLog("Detektujem nedostajuće zavisnosti...", "info");
      const res = await axios.get(`${API_BASE}/install/detect-missing`);
      setMissingPackages(res.data);

      const totalMissing = (res.data.python?.length || 0) + (res.data.node?.length || 0);
      if (totalMissing > 0) {
        addLog(`Pronađeno ${totalMissing} nedostajućih paketa`, "warning");
      } else {
        addLog("Sve zavisnosti su instalirane!", "success");
      }
    } catch (err) {
      addLog("Greška pri detekciji zavisnosti", "error");
    }
  };

  const installPackage = async (pkg, type, dev = false) => {
    setIsInstallingPackage(true);
    try {
      const endpoint = type === 'python' ? '/install/python' : '/install/node';
      addLog(`Instaliram ${type} paket: ${pkg}...`, "info");

      const res = await axios.post(`${API_BASE}${endpoint}`, { package: pkg, dev });

      if (res.data.success) {
        addLog(`✓ Uspešno instaliran: ${pkg}`, "success");
        fetchInstalledPackages();
        detectMissingPackages();
      } else {
        addLog(`✗ Greška: ${res.data.message}`, "error");
      }
    } catch (err) {
      addLog(`Greška pri instalaciji paketa`, "error");
    } finally {
      setIsInstallingPackage(false);
    }
  };

  const handleInstallNewPackage = () => {
    if (!newPackageName.trim()) return;

    installPackage(newPackageName, packageTab, isDevDependency);
    setNewPackageName('');
    setIsDevDependency(false);
  };

  const handleInstallMissing = async () => {
    const packagesToInstall = packageTab === 'python'
      ? missingPackages.python
      : missingPackages.node;

    for (const pkg of packagesToInstall) {
      await installPackage(pkg, packageTab);
    }
  };

  // SR: Integration Manager Functions (Git)
  const fetchGitStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/git/status`);
      if (res.data.initialized) {
        setGitStatus({ ...res.data.status, initialized: true });
      } else {
        setGitStatus({ modified: [], staged: [], untracked: [], initialized: false });
      }
    } catch (err) {
      addLog("Greška pri učitavanju Git statusa", "error");
    }
  };

  const handleGitInit = async () => {
    try {
      const res = await axios.post(`${API_BASE}/git/init`);
      if (res.data.success) {
        addLog("Git repozitorijum inicijalizovan", "success");
        fetchGitStatus();
      } else {
        addLog(`Greška: ${res.data.message}`, "error");
      }
    } catch (err) {
      addLog("Greška pri inicijalizaciji git-a", "error");
    }
  };

  const handleGitCommit = async () => {
    if (!commitMessage.trim()) return;
    try {
      const res = await axios.post(`${API_BASE}/git/commit`, { message: commitMessage });
      if (res.data.success) {
        addLog(`Commit uspešan: ${commitMessage}`, "success");
        setCommitMessage('');
        fetchGitStatus();
      } else {
        addLog(`Greška: ${res.data.message}`, "error");
      }
    } catch (err) {
      addLog("Greška pri kreiranju commit-a", "error");
    }
  };

  const handleGitPush = async () => {
    setIsPushing(true);
    try {
      addLog("Guram promene na remote...", "info");
      const res = await axios.post(`${API_BASE}/git/push`);
      if (res.data.success) {
        addLog("Push uspešan!", "success");
        fetchGitStatus();
      } else {
        addLog(`Greška: ${res.data.message}`, "error");
      }
    } catch (err) {
      addLog("Greška pri push-ovanju", "error");
    } finally {
      setIsPushing(false);
    }
  };

  // SR: Integration Manager Functions (Supabase)
  const handleSupabaseConnect = async () => {
    setIsConnectingSupabase(true);
    try {
      const res = await axios.post(`${API_BASE}/supabase/connect`, { url: supabaseUrl, key: supabaseKey });
      if (res.data.success) {
        addLog("Uspešno povezano sa Supabase!", "success");
        setSupabaseConnected(true);
        setSupabaseTables(res.data.tables);
      } else {
        addLog(`Greška pri povezivanju: ${res.data.message}`, "error");
        setSupabaseConnected(false);
      }
    } catch (err) {
      addLog("Greška pri povezivanju sa Supabase", "error");
    } finally {
      setIsConnectingSupabase(false);
    }
  };

  const fetchSupabaseTables = async () => {
    try {
      const res = await axios.get(`${API_BASE}/supabase/tables`);
      if (res.data.success) {
        setSupabaseTables(res.data.tables);
      }
    } catch (err) {
      addLog("Greška pri dohvatanju tabela", "error");
    }
  };

  const addLog = (msg, type = 'info') => {
    setLogs(prev => [...prev.slice(-49), { id: Date.now(), msg, type, time: new Date().toLocaleTimeString() }]);
  };

  const handleFileClick = async (file) => {
    // SR: Robusna normalizacija za Windows (lowercase + forward slashes)
    const normalize = (p) => p.replace(/[\\\/]+/g, '/').toLowerCase();
    const normalizedFile = normalize(file);

    // Ako je fajl već otvoren, samo se prebaci na njega
    const alreadyOpen = openFiles.find(f => normalize(f.path) === normalizedFile);
    if (alreadyOpen) {
      setActiveFile(alreadyOpen.path);
      setFileContent(alreadyOpen.content);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE}/read-file?path=${file}`);
      const displayPath = file.replace(currentPath, '').replace(/^[\\\/]+/, '');
      const newFileObj = {
        path: file,
        content: res.data.content,
        isDirty: false,
        targetFile: displayPath,
        messages: [{ id: Date.now(), text: `Započeli ste razgovor o fajlu: ${file.split(/[\\/]/).pop()}`, type: 'ai' }]
      };

      setOpenFiles(prev => [...prev, newFileObj]);
      setActiveFile(file);
      setFileContent(res.data.content);

      addLog(`Otvaranje: ${file.split('\\').pop()}`, 'info');
    } catch (err) {
      addLog(`Greška pri čitanju fajla`, 'error');
    }
  };

  const handleCloseTab = (e, path) => {
    e.stopPropagation();
    const newOpenFiles = openFiles.filter(f => f.path !== path);
    setOpenFiles(newOpenFiles);

    if (activeFile === path) {
      if (newOpenFiles.length > 0) {
        const nextFile = newOpenFiles[newOpenFiles.length - 1];
        setActiveFile(nextFile.path);
        setFileContent(nextFile.content);
      } else {
        setActiveFile(null);
        setFileContent('');
      }
    }
  };

  const handleEditorChange = (value) => {
    setFileContent(value);
    setOpenFiles(prev => prev.map(f =>
      f.path === activeFile ? { ...f, content: value, isDirty: true } : f
    ));
  };

  const handleSave = async () => {
    if (!activeFile) return;
    try {
      const res = await axios.post(`${API_BASE}/save-file?path=${activeFile}&content=${encodeURIComponent(fileContent)}`);
      if (res.data.success) {
        addLog(`✓ Sačuvano`, 'success');
        setOpenFiles(prev => prev.map(f =>
          f.path === activeFile ? { ...f, isDirty: false } : f
        ));
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
    if (!aiPrompt.trim() && attachments.length === 0) return;
    const chatOriginPath = activeFile; // SR: Putanja taba gde je razgovor počeo
    setLoading(true);

    const updateMessages = (updater) => {
      if (chatOriginPath) {
        // SR: Robusna normalizacija za Windows
        const normalize = (p) => p.replace(/[\\\/]+/g, '/').toLowerCase();
        const normOrigin = normalize(chatOriginPath);
        setOpenFiles(prev => prev.map(f =>
          normalize(f.path) === normOrigin ? { ...f, messages: updater(f.messages) } : f
        ));
      } else {
        setGlobalMessages(updater);
      }
    };

    addLog(`AI Robot: Izvršavam zadatak...`, 'info');
    try {
      // ... (payload logic)
      // SR: Automatski uključi AKTIVNI FAJL u kontekst ako postoji
      const finalAttachments = [...attachments.map(a => ({ type: a.type, data: a.data, name: a.name }))];

      if (activeFile && !finalAttachments.some(a => a.name === activeFile)) {
        finalAttachments.push({
          type: 'file',
          name: activeFile.split(/[\\\/]/).pop(),
          data: fileContent
        });
      }

      const currentTarget = chatOriginPath
        ? (openFiles.find(f => f.path === chatOriginPath)?.targetFile || globalTargetFile)
        : globalTargetFile;

      const payload = {
        prompt: aiPrompt,
        target_file: activeFile ? (openFiles.find(f => f.path === activeFile)?.targetFile || activeFile) : globalTargetFile,
        model: currentModel, // SR: Koristi izabrani model
        attachments: finalAttachments.map(att => ({
          name: att.name,
          type: att.type,
          data: att.data
        })),
        mode: chatMode // SR: Planning ili Act
      };

      const response = await fetch(`${API_BASE}/stream-generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_TOKEN // SR: Fixed missing header for stream
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Network response was not ok");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // Napomena: Placeholder poruke su već kreirane u handleSendMessage

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Obrada NDJSON linija
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Poslednja linija može biti nekompletna

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);

            if (data.type === 'chunk') {
              updateMessages(prev => prev.map(m => {
                // SR: Provera agentId (sa podrškom za snake_case i camelCase iz API-ja)
                // const dataAgentId = data.agent_id || data.agentId; // No longer needed for single agent
                if (m.isStreaming) {
                  return { ...m, text: (m.text || '') + data.content };
                }
                return m;
              }));
            } else if (data.type === 'preview') {
              addLog(`✋ Agent traži odobrenje za izmene`, 'warning');
              updateMessages(prev => prev.map(m => {
                // const dataAgentId = data.agent_id || data.agentId; // No longer needed for single agent
                return m.isStreaming ? {
                  ...m,
                  text: data.explanation,
                  preview: {
                    code: data.code,
                    filename: data.filename,
                    originalMessage: data.explanation
                  },
                  isStreaming: false
                } : m;
              }));
            } else if (data.type === 'security_warning') {
              addLog(`🚨 Pretnje detektovane: ${data.threats.join(', ')}`, 'error');
              updateMessages(prev => prev.map(m => {
                // const dataAgentId = data.agent_id || data.agentId; // No longer needed for single agent
                return m.isStreaming ? {
                  ...m,
                  text: (m.text || '') + `\n\n🚨 **SIGURNOSNO UPOZORENJE**: Blokirano zbog pretnji.`,
                  isStreaming: false
                } : m;
              }));
            }
            else if (data.type === 'done') {
              // addLog(`✓ Uspešno obavljeno!`, 'success');
              // Ne označavamo kraj globalno jer drugi agenti možda još rade
            }
          } catch (e) {
            console.error("Greška pri parsiranju stream-a", e);
          }
        }
      }

      addLog(`✓ Svi agenti završili!`, 'success');
      fetchStatus();
      setAiPrompt('');
      setAttachments([]);

    } catch (err) {
      addLog(`Greška API servisa: ${err.message}`, 'error');
    } finally {
      setLoading(false);
      // Oznaci sve poruke kao not streaming
      updateMessages(prev => prev.map(m => ({ ...m, isStreaming: false })));
    }
  };

  const handleApply = async (msgId, filename, content) => {
    try {
      addLog(`Primena izmena na ${filename}...`, 'info');
      const res = await axios.post(`${API_BASE}/apply-changes`, {
        filename,
        content
      });

      if (res.data.success) {
        addLog(`✓ Izmene uspešno primenjene!`, 'success');

        const updateMsgs = (prev) => prev.map(m =>
          m.id === msgId ? { ...m, text: `✅ Izmene odobrene i primenjene na ${filename}.`, preview: null } : m
        );

        if (activeFile) {
          // SR: Robusna normalizacija putanja za upis u tab
          const normalize = (p) => p.replace(/[\\\/]+/g, '/').toLowerCase();
          const targetNorm = normalize(activeFile);

          setOpenFiles(prev => prev.map(f =>
            normalize(f.path) === targetNorm ? { ...f, messages: updateMsgs(f.messages), content: content, isDirty: false } : f
          ));
        } else {
          setGlobalMessages(updateMsgs);
        }

        fetchStatus();

        // Ako je to trenutno aktivni fajl, osveži i editor state direktno
        const normalize = (p) => p.replace(/[\\\/]+/g, '/').toLowerCase();
        const normFilename = normalize(filename);
        if (activeFile && (normalize(activeFile) === normFilename || normalize(activeFile).endsWith(normFilename))) {
          setFileContent(content);
        }
      }
    } catch (err) {
      addLog(`Greška pri primeni izmena`, 'error');
    }
  };

  const handleDiscard = (msgId) => {
    const updateMsgs = (prev) => prev.map(m =>
      m.id === msgId ? { ...m, text: `❌ Izmene odbačene.`, preview: null } : m
    );

    if (activeFile) {
      setOpenFiles(prev => prev.map(f =>
        f.path === activeFile ? { ...f, messages: updateMsgs(f.messages) } : f
      ));
    } else {
      setGlobalMessages(updateMsgs);
    }

    addLog(`Izmene odbačene`, 'info');
  };

  const handleSendMessage = () => {
    if (!aiPrompt.trim() && attachments.length === 0) return;
    const userMsg = {
      id: Date.now(),
      text: aiPrompt || "Analiziraj priloženo...",
      type: 'user',
      hasAttachments: attachments.length > 0
    };

    const aiMessages = [];
    aiMessages.push({
      id: Date.now() + 1,
      text: '',
      type: 'ai',
      agentId: 'default', // SR: Uvek koristimo default za pojednostavljeni sistem
      agentName: 'AI Agent',
      agentColor: 'blue',
      agentModel: currentModel,
      isStreaming: true
    });

    // Ažuriraj odgovarajući bafer poruka
    const chatOriginPath = activeFile;
    if (chatOriginPath) {
      // SR: Robusna normalizacija za Windows
      const normalize = (p) => p.replace(/[\\\/]+/g, '/').toLowerCase();
      const normOrigin = normalize(chatOriginPath);
      setOpenFiles(prev => prev.map(f =>
        normalize(f.path) === normOrigin ? { ...f, messages: [...(f.messages || []), userMsg, ...aiMessages] } : f
      ));
    } else {
      setGlobalMessages(prev => [...prev, userMsg, ...aiMessages]);
    }

    handleGenerate();
  };

  const handlePaste = (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let index in items) {
      const item = items[index];
      if (item.kind === 'file') {
        const blob = item.getAsFile();
        const reader = new FileReader();
        reader.onload = (event) => {
          setAttachments(prev => [...prev, {
            id: Date.now() + Math.random(),
            type: blob.type.startsWith('image/') ? 'image' : 'file',
            name: blob.name || `Pasted Image ${new Date().toLocaleTimeString()}`,
            data: event.target.result
          }]);
        };
        if (blob.type.startsWith('image/')) {
          reader.readAsDataURL(blob);
        } else {
          reader.readAsText(blob);
        }
      }
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    selectedFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        setAttachments(prev => [...prev, {
          id: Date.now() + Math.random(),
          type: file.type.startsWith('image/') ? 'image' : 'file',
          name: file.name,
          data: event.target.result
        }]);
      };
      if (file.type.startsWith('image/')) {
        reader.readAsDataURL(file);
      } else {
        reader.readAsText(file);
      }
    });
  };

  const removeAttachment = (id) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  };

  return (
    <div className={`flex h-screen bg-vscode-bg text-vscode-text font-sans overflow-hidden theme-dark`}>
      {/* Activity Bar */}
      <div className="w-12 bg-vscode-activity flex flex-col items-center py-4 space-y-4 border-r border-vscode-border z-20 shrink-0">
        <div
          className="p-2 cursor-pointer text-vscode-accent hover:text-white transition-transform active:scale-95"
          title="Promeni temu (Dark / Navy / Tokyo Night)"
        >
          <Activity size={24} />
        </div>
        <div className="w-8 h-[1px] bg-white/10" />
        <div
          className={`p-2 cursor-pointer transition-colors ${leftSidebarMode === 'explorer' && leftSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => {
            if (leftSidebarMode === 'explorer') setLeftSidebarVisible(!leftSidebarVisible);
            else { setLeftSidebarMode('explorer'); setLeftSidebarVisible(true); }
          }}
          title="Explorer (Fajlovi)"
        >
          <Files size={24} />
        </div>
        <div
          className={`p-2 cursor-pointer transition-colors ${leftSidebarMode === 'search' && leftSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => {
            if (leftSidebarMode === 'search') setLeftSidebarVisible(!leftSidebarVisible);
            else { setLeftSidebarMode('search'); setLeftSidebarVisible(true); }
          }}
          title="Pretraga projekta"
        >
          <Search size={24} />
        </div>
        <div
          className={`p-2 cursor-pointer transition-colors ${leftSidebarMode === 'packages' && leftSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => {
            if (leftSidebarMode === 'packages') setLeftSidebarVisible(!leftSidebarVisible);
            else { setLeftSidebarMode('packages'); setLeftSidebarVisible(true); fetchInstalledPackages(); detectMissingPackages(); }
          }}
          title="Package Manager"
        >
          <Package size={24} />
        </div>
        <div
          className={`p-2 cursor-pointer transition-colors ${leftSidebarMode === 'integration' && leftSidebarVisible ? 'text-white' : 'text-gray-500 hover:text-white'}`}
          onClick={() => {
            if (leftSidebarMode === 'integration') setLeftSidebarVisible(!leftSidebarVisible);
            else { setLeftSidebarMode('integration'); setLeftSidebarVisible(true); fetchGitStatus(); }
          }}
          title="Integrations (GitHub, Vercel, Supabase)"
        >
          <Link size={24} />
        </div>
        <div
          className={`p-2 cursor-pointer transition-colors ${showConsole ? 'text-white bg-white/10 rounded' : 'text-gray-500 hover:text-white'}`}
          onClick={() => setShowConsole(!showConsole)}
          title="Terminal (Console)"
        >
          <TerminalIcon size={24} />
        </div>
        <div
          className="p-2 text-gray-800 opacity-20 pointer-events-none cursor-default"
          title="Upravljanje Agentima (Uskoro...)"
        >
          <Users size={24} />
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
              <div
                className="p-4 uppercase text-[12px] font-bold tracking-widest text-[#888] flex justify-between items-center bg-black/10"
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const droppedFiles = e.dataTransfer.files;
                  if (droppedFiles.length > 0) {
                    // SR: Ako browser podržava path (kao što je slučaj kod nekih lokalnih setupa)
                    const path = droppedFiles[0].path;
                    if (path) {
                      setCurrentPath(path);
                      setTimeout(handleSetPath, 100);
                    } else {
                      addLog("Prevlačenje foldera nije podržano u ovom browseru - koristite dugme!", "warning");
                    }
                  }
                }}
              >
                <span>{leftSidebarMode === 'explorer' ? 'Explorer' : leftSidebarMode === 'agents' ? 'Agenti' : 'Pretraga'}</span>
                {leftSidebarMode === 'explorer' && <Plus className="cursor-pointer hover:text-white" size={17} onClick={handleBrowseFile} />}
              </div>

              {leftSidebarMode === 'explorer' ? (
                <>
                  <div className="p-3 border-y border-white/5 space-y-2 bg-[#252526]/50">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-gray-500 font-bold uppercase">Radni Folderi</span>
                      <div className="flex gap-1">
                        <button onClick={handleBrowse} className="p-1 hover:bg-white/10 rounded text-vscode-accent" title="Promeni glavni folder"><FolderOpen size={14} /></button>
                        <button onClick={handleAddFolder} className="p-1 hover:bg-white/10 rounded text-vscode-accent" title="Dodaj folder"><Plus size={14} /></button>
                      </div>
                    </div>

                    {roots.length > 0 ? (
                      <div className="flex flex-col gap-1 max-h-[100px] overflow-y-auto custom-scrollbar">
                        {roots.map((root, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-[11px] text-vscode-text bg-[#1e1e1e] px-2 py-1 rounded border border-white/10 group relative" title={root}>
                            <FolderOpen size={12} className="text-gray-500 shrink-0" />
                            <span className="truncate flex-grow">{root.split(/[\\/]/).pop()}</span>
                            {/* Ne dozvoljavamo uklanjanje primarnog foldera (indeks 0) */}
                            {idx > 0 && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleRemoveFolder(root); }}
                                className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-500/20 rounded text-red-500 transition-opacity"
                                title="Ukloni iz radnog prostora"
                              >
                                <X size={10} />
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <input
                        type="text"
                        className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1 text-[12px] focus:outline-none focus:border-vscode-accent/50 text-vscode-text"
                        value={currentPath}
                        onChange={(e) => setCurrentPath(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSetPath()}
                      />
                    )}
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
                </>
              ) : leftSidebarMode === 'agents' ? (
                <div className="flex flex-col flex-grow overflow-hidden bg-[#1e1e1e]">
                  <div className="p-4 border-b border-white/5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[12px] font-bold uppercase text-gray-500">Agenti</h3>
                      <button onClick={() => setIsAddingAgent(!isAddingAgent)} className="text-vscode-accent hover:text-white p-1">
                        <Plus size={16} />
                      </button>
                    </div>

                    {isAddingAgent && (
                      <div className="bg-[#252526] p-3 rounded border border-white/10 space-y-2 animate-in fade-in slide-in-from-top-2">
                        <input
                          className="w-full bg-[#3c3c3c] rounded px-2 py-1 text-[12px] text-white focus:outline-none border border-transparent focus:border-vscode-accent"
                          placeholder="Ime agenta (npr. Tester)"
                          value={newAgentName}
                          onChange={e => setNewAgentName(e.target.value)}
                        />
                        <textarea
                          className="w-full bg-[#3c3c3c] rounded px-2 py-1 text-[12px] text-white focus:outline-none border border-transparent focus:border-vscode-accent h-20 resize-none"
                          placeholder="Uloga (System Prompt)..."
                          value={newAgentRole}
                          onChange={e => setNewAgentRole(e.target.value)}
                        />
                        <button
                          onClick={handleCreateAgent}
                          className="w-full bg-[#0e639c] hover:bg-[#1177bb] text-white text-[11px] py-1 rounded font-bold"
                        >
                          Kreiraj Agenta
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="flex-grow overflow-y-auto custom-scrollbar p-2 space-y-2">
                    {agents.map(agent => (
                      <div key={agent.id} className="bg-[#252526] p-3 rounded border border-white/5 hover:border-white/10 transition-colors group">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-gray-600'}`} />
                            <span className={`font-bold text-[13px] ${agent.is_active ? 'text-white' : 'text-gray-400'}`}>{agent.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full border border-white/20`} style={{ backgroundColor: agent.color }} title="Boja agenta" />
                            <input
                              type="checkbox"
                              checked={agent.is_active}
                              onChange={() => toggleAgent(agent.id, agent.is_active)}
                              className="cursor-pointer"
                              title="Aktiviraj/Deaktiviraj"
                            />
                          </div>
                        </div>
                        <p className="text-[11px] text-gray-500 line-clamp-2" title={agent.role}>{agent.role}</p>
                        <div className="mt-2 text-[10px] text-gray-600 font-mono">{agent.model}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : leftSidebarMode === 'search' ? (
                <div className="flex flex-col flex-grow overflow-hidden">
                  <div className="p-4 space-y-3">
                    <input
                      type="text"
                      autoFocus
                      placeholder="Pretraži tekst..."
                      className="w-full bg-vscode-input border border-white/10 rounded px-3 py-2 text-[14px] focus:outline-none focus:border-vscode-accent text-vscode-text"
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                    />
                    <div className="text-[10px] text-gray-500 uppercase font-bold tracking-tight">
                      {isSearching ? 'Tražim...' : `${searchResults.length} rezultata`}
                    </div>
                  </div>
                  <div className="flex-grow overflow-y-auto custom-scrollbar">
                    {searchResults.map((res, idx) => (
                      <div
                        key={idx}
                        className="px-4 py-2 border-b border-white/5 hover:bg-white/5 cursor-pointer group"
                        onClick={() => handleFileClick(res.file)}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[13px] text-vscode-accent font-medium truncate max-w-[180px]">{res.file.split(/[\\\/]/).pop()}</span>
                          <span className="text-[10px] text-gray-500">Linija {res.line}</span>
                        </div>
                        <div className="text-[11px] text-gray-400 truncate font-mono italic">
                          {res.content}
                        </div>
                      </div>
                    ))}
                    {!isSearching && searchResults.length === 0 && searchQuery.length >= 2 && (
                      <div className="p-8 text-center text-gray-600 text-[12px] italic">Nema pronađenih rezultata</div>
                    )}
                  </div>
                </div>
              ) : leftSidebarMode === 'packages' ? (
                <div className="flex flex-col flex-grow overflow-hidden bg-[#1e1e1e]">
                  {/* Package Manager Header */}
                  <div className="p-4 border-b border-white/5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[12px] font-bold uppercase text-gray-500">Package Manager</h3>
                      <button
                        onClick={detectMissingPackages}
                        className="text-[10px] px-2 py-1 bg-vscode-accent/20 hover:bg-vscode-accent/30 text-vscode-accent rounded transition-colors"
                      >
                        Detect Missing
                      </button>
                    </div>

                    {/* Tab Switcher */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPackageTab('python')}
                        className={`flex-1 px-3 py-1.5 text-[11px] font-medium rounded transition-colors ${packageTab === 'python'
                          ? 'bg-vscode-accent text-white'
                          : 'bg-[#252526] text-gray-400 hover:text-white'
                          }`}
                      >
                        Python
                      </button>
                      <button
                        onClick={() => setPackageTab('node')}
                        className={`flex-1 px-3 py-1.5 text-[11px] font-medium rounded transition-colors ${packageTab === 'node'
                          ? 'bg-vscode-accent text-white'
                          : 'bg-[#252526] text-gray-400 hover:text-white'
                          }`}
                      >
                        Node.js
                      </button>
                    </div>

                    {/* Install New Package */}
                    <div className="bg-[#252526] p-3 rounded border border-white/10 space-y-2">
                      <input
                        type="text"
                        placeholder={`Enter ${packageTab} package name...`}
                        value={newPackageName}
                        onChange={(e) => setNewPackageName(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleInstallNewPackage()}
                        className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1.5 text-[12px] focus:outline-none focus:border-vscode-accent/50 text-vscode-text"
                      />
                      {packageTab === 'node' && (
                        <label className="flex items-center gap-2 text-[11px] text-gray-400 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isDevDependency}
                            onChange={(e) => setIsDevDependency(e.target.checked)}
                            className="rounded"
                          />
                          Dev Dependency
                        </label>
                      )}
                      <button
                        onClick={handleInstallNewPackage}
                        disabled={isInstallingPackage || !newPackageName.trim()}
                        className="w-full px-3 py-1.5 bg-vscode-accent hover:bg-vscode-accent/80 disabled:bg-gray-700 disabled:text-gray-500 text-white text-[11px] font-bold rounded transition-colors"
                      >
                        {isInstallingPackage ? 'Installing...' : 'Install Package'}
                      </button>
                    </div>
                  </div>

                  {/* Missing Packages Warning */}
                  {(packageTab === 'python' ? missingPackages.python : missingPackages.node)?.length > 0 && (
                    <div className="p-3 bg-yellow-500/10 border-b border-yellow-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 text-[11px] text-yellow-500">
                          <AlertCircle size={14} />
                          <span className="font-bold">
                            {(packageTab === 'python' ? missingPackages.python : missingPackages.node).length} Missing
                          </span>
                        </div>
                        <button
                          onClick={handleInstallMissing}
                          className="text-[10px] px-2 py-1 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-500 rounded transition-colors"
                        >
                          Install All
                        </button>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {(packageTab === 'python' ? missingPackages.python : missingPackages.node).map(pkg => (
                          <span key={pkg} className="text-[10px] px-2 py-0.5 bg-yellow-500/20 text-yellow-500 rounded">
                            {pkg}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Installed Packages List */}
                  <div className="flex-grow overflow-y-auto custom-scrollbar">
                    <div className="px-4 py-2 text-[12px] text-gray-500 font-bold uppercase">
                      Installed {packageTab === 'python' ? 'Python' : 'Node.js'} Packages
                    </div>
                    {packageTab === 'python' ? (
                      installedPythonPackages.length > 0 ? (
                        installedPythonPackages
                          .filter(pkg => pkg.name.toLowerCase().includes(packageSearchQuery.toLowerCase()))
                          .map(pkg => (
                            <div
                              key={pkg.name}
                              className="flex items-center justify-between px-4 py-2 hover:bg-white/5 text-[13px] border-b border-white/5"
                            >
                              <div className="flex items-center gap-2">
                                <Package size={14} className="text-vscode-accent" />
                                <span className="text-vscode-text">{pkg.name}</span>
                              </div>
                              <span className="text-[11px] text-gray-500">{pkg.version}</span>
                            </div>
                          ))
                      ) : (
                        <div className="p-4 text-[12px] text-gray-600 italic">No packages installed</div>
                      )
                    ) : (
                      <div className="p-4 text-[12px] text-gray-600 italic">
                        Check package.json for Node.js packages
                      </div>
                    )}
                  </div>
                </div>
              ) : leftSidebarMode === 'integration' ? (
                <div className="flex flex-col flex-grow overflow-hidden bg-[#1e1e1e]">
                  {/* Integration Manager Header */}
                  <div className="p-4 border-b border-white/5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-[12px] font-bold uppercase text-gray-500">Integrations</h3>
                      <div className="flex gap-2">
                        <button
                          onClick={fetchGitStatus}
                          className="text-gray-400 hover:text-white transition-colors"
                          title="Refresh Status"
                        >
                          <Activity size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Integration Tabs */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => setIntegrationMode('github')}
                        className={`flex-1 px-3 py-1.5 text-[11px] font-medium rounded transition-colors flex items-center justify-center gap-2 ${integrationMode === 'github'
                          ? 'bg-vscode-accent text-white'
                          : 'bg-[#252526] text-gray-400 hover:text-white'
                          }`}
                      >
                        <Link size={12} /> GitHub
                      </button>
                      <button
                        onClick={() => setIntegrationMode('vercel')}
                        className={`flex-1 px-3 py-1.5 text-[11px] font-medium rounded transition-colors flex items-center justify-center gap-2 ${integrationMode === 'vercel'
                          ? 'bg-vscode-accent text-white'
                          : 'bg-[#252526] text-gray-400 hover:text-white'
                          }`}
                      >
                        <Zap size={12} /> Vercel
                      </button>
                      <button
                        onClick={() => setIntegrationMode('supabase')}
                        className={`flex-1 px-3 py-1.5 text-[11px] font-medium rounded transition-colors flex items-center justify-center gap-2 ${integrationMode === 'supabase'
                            ? 'bg-vscode-accent text-white'
                            : 'bg-[#252526] text-gray-400 hover:text-white'
                          }`}
                      >
                        <Database size={12} /> Supabase
                      </button>
                    </div>

                    {/* GitHub Integration Content */}
                    {integrationMode === 'github' && (
                      <div className="space-y-3">
                        {!gitStatus.initialized ? (
                          <div className="p-4 bg-[#252526] rounded border border-white/10 text-center space-y-3">
                            <div className="text-gray-400 text-[12px]">Git repozitorijum nije inicijalizovan.</div>
                            <button
                              onClick={handleGitInit}
                              className="w-full px-3 py-1.5 bg-vscode-accent hover:bg-vscode-accent/80 text-white text-[11px] font-bold rounded transition-colors"
                            >
                              Inicijalizuj Git
                            </button>
                          </div>
                        ) : (
                          <>
                            {/* Commit Section */}
                            <div className="bg-[#252526] p-3 rounded border border-white/10 space-y-2">
                              <textarea
                                placeholder="Commit poruka..."
                                value={commitMessage}
                                onChange={(e) => setCommitMessage(e.target.value)}
                                className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1.5 text-[12px] focus:outline-none focus:border-vscode-accent/50 text-vscode-text min-h-[60px] resize-none"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={handleGitCommit}
                                  disabled={!commitMessage.trim()}
                                  className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-[11px] font-bold rounded transition-colors flex items-center justify-center gap-2"
                                >
                                  <Check size={12} /> Commit
                                </button>
                                <button
                                  onClick={handleGitPush}
                                  disabled={isPushing}
                                  className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-[11px] font-bold rounded transition-colors flex items-center justify-center gap-2"
                                >
                                  {isPushing ? 'Pushing...' : 'Push'}
                                </button>
                              </div>
                            </div>

                            {/* Changes List */}
                            <div className="space-y-1">
                              <div className="flex items-center justify-between px-1">
                                <span className="text-[11px] font-bold text-gray-500 uppercase">Promene</span>
                                <span className="text-[10px] bg-vscode-accent/20 text-vscode-accent px-1.5 rounded-full">
                                  {gitStatus.modified.length + gitStatus.untracked.length}
                                </span>
                              </div>
                              <div className="max-h-[300px] overflow-y-auto custom-scrollbar space-y-0.5">
                                {[...gitStatus.modified, ...gitStatus.untracked].length === 0 ? (
                                  <div className="text-[11px] text-gray-500 italic p-2 text-center">Nema promena</div>
                                ) : (
                                  [...gitStatus.modified, ...gitStatus.untracked].map((file, idx) => (
                                    <div key={idx} className="flex items-center gap-2 px-2 py-1 hover:bg-white/5 rounded group cursor-pointer text-[12px]">
                                      <span className="text-yellow-500 text-[10px]">M</span>
                                      <span className="text-gray-300 truncate">{file}</span>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {/* Vercel Content Placeholder */}
                    {integrationMode === 'vercel' && (
                      <div className="p-8 text-center text-gray-500 text-[12px] italic">
                        Vercel integracija uskoro...
                      </div>
                    )}

                    {/* Supabase Integration Content */}
                    {integrationMode === 'supabase' && (
                      <div className="space-y-3">
                        {!supabaseConnected ? (
                          <div className="bg-[#252526] p-3 rounded border border-white/10 space-y-2">
                            <div className="text-[11px] text-gray-400 mb-1">Povezivanje sa bazom</div>
                            <input
                              type="text"
                              placeholder="Supabase Project URL"
                              value={supabaseUrl}
                              onChange={(e) => setSupabaseUrl(e.target.value)}
                              className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1.5 text-[11px] focus:outline-none focus:border-vscode-accent/50 text-vscode-text"
                            />
                            <input
                              type="password"
                              placeholder="Supabase Anon Key"
                              value={supabaseKey}
                              onChange={(e) => setSupabaseKey(e.target.value)}
                              className="w-full bg-[#1e1e1e] border border-white/10 rounded px-2 py-1.5 text-[11px] focus:outline-none focus:border-vscode-accent/50 text-vscode-text"
                            />
                            <button
                              onClick={handleSupabaseConnect}
                              disabled={isConnectingSupabase || !supabaseUrl || !supabaseKey}
                              className="w-full px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-[11px] font-bold rounded transition-colors"
                            >
                              {isConnectingSupabase ? 'Povezivanje...' : 'Connect Supabase'}
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="flex items-center justify-between p-2 bg-green-500/10 border border-green-500/20 rounded">
                              <div className="flex items-center gap-2 text-green-500 text-[11px] font-bold">
                                <Check size={14} /> Connected
                              </div>
                              <button
                                onClick={() => setSupabaseConnected(false)}
                                className="text-[10px] text-gray-400 hover:text-white"
                              >
                                Disconnect
                              </button>
                            </div>

                            <div className="space-y-1">
                              <div className="flex items-center justify-between px-1">
                                <span className="text-[11px] font-bold text-gray-500 uppercase">Tabele</span>
                                <button onClick={fetchSupabaseTables} className="text-gray-400 hover:text-white"><Activity size={12} /></button>
                              </div>
                              <div className="max-h-[300px] overflow-y-auto custom-scrollbar space-y-0.5">
                                {supabaseTables.length === 0 ? (
                                  <div className="text-[11px] text-gray-500 italic p-2 text-center">Nema tabela</div>
                                ) : (
                                  supabaseTables.map((table, idx) => (
                                    <div key={idx} className="flex items-center gap-2 px-2 py-1 hover:bg-white/5 rounded group cursor-pointer text-[12px]">
                                      <Database size={12} className="text-vscode-accent" />
                                      <span className="text-gray-300 truncate">{table}</span>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
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
        {/* Tab Bar */}
        {openFiles.length > 0 && (
          <div className="flex bg-[#252526] border-b border-vscode-border overflow-x-auto no-scrollbar shrink-0 h-9 items-center">
            {openFiles.map(file => {
              const fileName = file.path.split(/[\\\/]/).pop();
              const isActive = activeFile === file.path;
              return (
                <div
                  key={file.path}
                  onClick={() => { setActiveFile(file.path); setFileContent(file.content); }}
                  className={`flex items-center gap-2 px-3 h-full cursor-pointer text-[12px] border-r border-vscode-border min-w-[120px] max-w-[200px] transition-colors relative group
                    ${isActive ? 'bg-[#1e1e1e] text-blue-400 border-t-2 border-vscode-accent' : 'bg-[#2d2d2d]/30 text-gray-500 hover:bg-white/5 hover:text-gray-300'}
                  `}
                >
                  <FileCode size={14} className={isActive ? 'text-blue-400' : 'text-gray-500'} />
                  <span className="truncate flex-grow">{fileName}{file.isDirty ? '*' : ''}</span>
                  <button
                    onClick={(e) => handleCloseTab(e, file.path)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-white/10 rounded transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="h-10 bg-vscode-sidebar border-b border-vscode-border flex items-center px-4 justify-between shrink-0">
          <div className="flex items-center text-[14px] truncate max-w-[70%]">
            {activeFile ? (
              <div className="flex items-center gap-2 text-gray-400 text-[11px] uppercase tracking-wider">
                <span className="opacity-50">Editor</span>
                <ChevronRight size={12} className="opacity-30" />
                <span className="truncate italic font-medium">{activeFile}</span>
              </div>
            ) : <span className="text-[#555] italic text-[14px]">Otvori bilo koji fajl iz Explorera</span>}
          </div>
          <div className="flex items-center gap-1">
            <button onClick={handleSave} disabled={!activeFile} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white disabled:opacity-20" title="Sačuvaj (Ctrl+S)">
              <Save size={16} />
            </button>
            <button onClick={() => { setActiveFile(null); setFileContent(''); }} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Zatvori Editor"><X size={16} /></button>
          </div>
        </div>

        <div className="flex-grow relative overflow-hidden">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="navy-theme"
            beforeMount={handleEditorWillMount}
            value={fileContent}
            onChange={handleEditorChange}
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
          {/* SR: Header Bar (Cursor Style) */}
          <div className="flex px-4 items-center justify-between shrink-0 h-10 border-b border-vscode-border bg-[#0a192f]">
            <div className="flex items-center gap-2 text-[11px] text-gray-400">
              <ChevronRight size={14} className="opacity-50" />
              <span>0 Files With Changes</span>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1 bg-[#233554] hover:bg-[#324b7a] transition-colors rounded text-[11px] text-[#64ffda] font-medium border border-[#64ffda]/20 shadow-lg group">
              <Check size={12} className="group-hover:scale-110 transition-transform" />
              Review Changes
            </button>
          </div>

          <div className="flex-grow overflow-hidden flex flex-col bg-[#f8f9fa]"> {/* Pearl White Background for Chat Area */}
            {/* Chat History View */}
            <div className="flex-grow overflow-y-auto custom-scrollbar p-4 space-y-4">
              {(activeFile ? (openFiles.find(f => f.path === activeFile)?.messages || []) : globalMessages).map(msg => (
                <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-xl text-[18px] leading-snug shadow-sm overflow-hidden ${msg.type === 'user'
                    ? 'bg-[#006d77] text-white rounded-tr-none' // Petroleum User Msg
                    : 'bg-white border border-gray-200 text-[#0a192f] rounded-tl-none shadow-md' // Pearl/White AI Msg with Navy Text
                    }`}>
                    {msg.type === 'ai' ? (
                      <div className="space-y-1.5 compact-markdown">
                        <ReactMarkdown
                          rehypePlugins={[rehypeHighlight]}
                          components={{
                            p: ({ node, ...props }) => <p className="my-1" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-1" {...props} />,
                            ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-1" {...props} />,
                            li: ({ node, ...props }) => <li className="my-0.5" {...props} />,
                            code({ node, inline, className, children, ...props }) {
                              return !inline ? (
                                <div className="my-2 rounded-md overflow-hidden border border-gray-200 bg-gray-50">
                                  <div className="bg-gray-100 px-3 py-1 text-[10px] text-gray-500 border-b border-gray-200 flex justify-between">
                                    <span>CODE</span>
                                  </div>
                                  <code className={`${className} block p-3 text-[17px] font-mono text-[#0a192f] leading-snug`} {...props}>
                                    {children}
                                  </code>
                                </div>
                              ) : (
                                <code className="bg-gray-100 px-1 py-0.5 rounded text-[14px] font-mono text-pink-600" {...props}>
                                  {children}
                                </code>
                              )
                            },
                            strong: ({ node, ...props }) => <strong className="text-[#8b0000] font-bold" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2 space-y-1" {...props} />,
                            ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2 space-y-1" {...props} />,
                            li: ({ node, ...props }) => <li className="pl-1" {...props} />
                          }}
                        >
                          {msg.text}
                        </ReactMarkdown>

                        {/* SR: Model Badge */}
                        {msg.agentModel && (
                          <div className="mt-2 pt-2 border-t border-gray-100">
                            <span className="inline-block bg-[#64ffda]/10 text-[#006d77] text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wide">
                              {msg.agentModel.replace('gemini/', '').replace('gpt-', 'GPT-').replace('claude-', 'Claude ')}
                            </span>
                          </div>
                        )}

                        {/* SR: PREVIEW UI BLOK */}
                        {msg.preview && (
                          <div className="mt-3 bg-white border border-vscode-accent/50 rounded-lg overflow-hidden shadow-sm">
                            <div className="bg-[#64ffda]/10 px-3 py-2 border-b border-[#64ffda]/20 flex items-center gap-2">
                              <AlertCircle size={14} className="text-[#006d77]" />
                              <span className="text-[11px] font-bold text-[#006d77] uppercase">Proposed Changes</span>
                              <span className="text-[10px] text-gray-500 ml-auto">{msg.preview.filename}</span>
                            </div>
                            <div className="p-3 bg-[#f8f9fa] max-h-60 overflow-y-auto custom-scrollbar border-b border-gray-100">
                              <pre className="text-[11px] font-mono text-[#0a192f] whitespace-pre-wrap">{msg.preview.code}</pre>
                            </div>
                            <div className="p-2 flex gap-2 bg-gray-50">
                              <button
                                onClick={() => handleApply(msg.id, msg.preview.filename, msg.preview.code)}
                                className="flex-1 bg-green-600 hover:bg-green-500 text-white text-[11px] font-bold py-1.5 rounded flex items-center justify-center gap-1 transition-colors"
                              >
                                <Check size={12} /> Apply
                              </button>
                              <button
                                onClick={() => handleDiscard(msg.id)}
                                className="flex-1 bg-red-600/80 hover:bg-red-500 text-white text-[11px] font-bold py-1.5 rounded flex items-center justify-center gap-1 transition-colors"
                              >
                                <X size={12} /> Discard
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      msg.text
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* SR: Modern Chat Input Area (Cursor Style) */}
            <div className="p-4 bg-vscode-sidebar border-t border-vscode-border shrink-0 flex flex-col gap-2 z-50">
              <div className="relative bg-[#0a192f]/80 backdrop-blur-md border border-[#233554] rounded-xl shadow-2xl overflow-hidden group hover:border-[#64ffda]/30 transition-all focus-within:border-[#64ffda]/50">
                {/* Attachment Previews */}
                {attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2 p-3 bg-white/5 border-b border-white/10 max-h-32 overflow-y-auto custom-scrollbar">
                    {attachments.map(att => (
                      <div key={att.id} className="relative group/att flex items-center gap-2 bg-vscode-activity p-2 rounded border border-white/10 shadow-sm">
                        {att.type === 'image' ? (
                          <img src={att.data} alt={att.name} className="w-8 h-8 rounded object-cover" />
                        ) : (
                          <FileText size={16} className="text-[#64ffda]" />
                        )}
                        <span className="text-[10px] text-gray-300 truncate max-w-[100px]">{att.name}</span>
                        <button
                          onClick={() => removeAttachment(att.id)}
                          className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover/att:opacity-100 transition-opacity"
                        >
                          <X size={10} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <textarea
                  className="w-full bg-transparent border-none rounded-t-xl p-4 text-[18px] h-24 focus:outline-none resize-none placeholder:text-gray-500 text-white scrollbar-hide"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Pitajte agenta ili unesite komandu..."
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendMessage())}
                />

                {/* Bottom Bar Tools */}
                <div className="flex items-center justify-between px-3 py-2 bg-white/5 border-t border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 group/mode relative">
                      <button
                        onClick={() => setChatMode(prev => prev === 'Planning' ? 'Act' : 'Planning')}
                        className="flex items-center gap-1.5 px-2 py-1 hover:bg-white/10 rounded transition-colors text-white/60 hover:text-white"
                      >
                        <Zap size={14} className={chatMode === 'Act' ? "text-[#f78c6c]" : "text-gray-400"} />
                        <span className="text-[11px] font-medium">{chatMode}</span>
                        <ChevronDown size={10} />
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button onClick={() => fileInputRef.current.click()} className="p-1.5 hover:bg-white/10 rounded text-white/40 hover:text-white transition-colors" title="Dodaj fajlove">
                      <Paperclip size={18} />
                    </button>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={handleCopyChat}
                        className="p-1.5 text-gray-500 hover:text-vscode-accent hover:bg-white/5 rounded transition-colors"
                        title="Kopiraj ceo razgovor (Markdown)"
                      >
                        <Copy size={16} />
                      </button>
                      <button
                        onClick={() => setIsChatMaximized(!isChatMaximized)}
                        className="p-1.5 text-gray-500 hover:text-vscode-accent hover:bg-white/5 rounded transition-colors"
                        title={isChatMaximized ? "Smanji čat" : "Proširi čat"}
                      >
                        {isChatMaximized ? <ChevronRight size={18} /> : <Plus size={18} />}
                      </button>
                    </div>
                    <button className="p-1.5 hover:bg-white/10 rounded text-white/40 hover:text-white transition-colors" title="Glasovni unos">
                      <Mic size={18} />
                    </button>
                    <button
                      onClick={() => { if (!loading) handleSendMessage() }}
                      className={`p-2 transition-all rounded-lg shadow-lg ${loading ? 'bg-red-500 text-white scale-110' : 'bg-[#64ffda] text-[#0a192f] hover:bg-[#a50000] hover:text-white active:scale-95'}`}
                      title={loading ? "Prekini generisanje" : "Pošalji (Enter)"}
                    >
                      {loading ? <Square size={16} fill="white" /> : <ChevronRight size={18} />}
                    </button>
                  </div>
                </div>
              </div>

              <input
                type="file"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>
          </div>
        </div>

        {/* Floating AI Agent Console */}
        <AnimatePresence>
          {showConsole && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              style={{
                position: 'fixed',
                left: consolePos.x,
                top: consolePos.y,
                width: consoleSize.width,
                height: consoleSize.height,
                zIndex: 1000,
              }}
              className="bg-vscode-sidebar border border-vscode-border rounded-xl shadow-2xl flex flex-col overflow-hidden"
            >
              {/* Header / Drag Bar */}
              <div
                onMouseDown={startDragging}
                className="p-3 flex items-center justify-between border-b border-vscode-border bg-[#0d1b2e] cursor-move select-none shrink-0"
              >
                <div className="flex items-center gap-2">
                  <TerminalIcon size={16} className="text-[#64ffda]" />
                  <span className="text-[12px] font-bold uppercase tracking-widest text-[#64ffda]">Output Console</span>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => setShowConsole(false)} className="hover:text-white text-gray-400">
                    <X size={16} />
                  </button>
                </div>
              </div>

              {/* Console Logs */}
              <div className="flex-grow overflow-y-auto p-4 font-mono text-[13px] space-y-1 bg-[#0a192f] custom-scrollbar">
                {logs.map(log => (
                  <div key={log.id} className="flex gap-3">
                    <span className="text-gray-500 shrink-0">[{log.time}]</span>
                    <span className={log.type === 'success' ? 'text-green-400' : log.type === 'error' ? 'text-red-400' : log.type === 'warning' ? 'text-yellow-400' : 'text-white'}>
                      {log.msg}
                    </span>
                  </div>
                ))}
                {logs.length === 0 && <div className="text-gray-500 italic">Sistem spreman.</div>}
                <div ref={chatEndRef} />
              </div>

              {/* Status Bar */}
              <div className="p-3 bg-black/40 border-t border-white/5 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-4 text-[11px] text-gray-500 uppercase">
                  <div className="flex items-center gap-1">
                    <span>PROJEKAT:</span>
                    <span className="text-vscode-text font-medium">{currentPath.split(/[\\\/]/).pop() || 'N/A'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span>TOKENS:</span>
                    <span className="text-vscode-accent font-bold">{status?.total_tokens || 0}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${loading ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`} />
                  <span className="text-[10px] text-gray-400 uppercase font-bold">{loading ? 'Processing' : 'Idle'}</span>
                </div>
              </div>

              {/* Resize Handle */}
              <div
                onMouseDown={startResizingConsole}
                className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize flex items-center justify-center group"
              >
                <div className="w-1.5 h-1.5 border-r border-b border-gray-600 group-hover:border-vscode-accent" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
