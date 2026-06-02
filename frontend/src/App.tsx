import React, { useState, useEffect, useTransition } from "react";
import {
  RefreshCw, Wifi, WifiOff, Sparkles,
  ShieldAlert, Hotel, Settings, UserCircle, Menu, X, MessageSquare, Clock, Download
} from "lucide-react";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import { Message, SystemHealth, ChatSession } from "./types";
import { ChatConsole } from "./components/chat-console";
import { InspectorDrawer } from "./components/inspector-drawer";
import { createSession, deleteSession, submitChatTurn, checkApiHealth } from "./services/api";

const HISTORY_STORAGE_KEY = "staychat_history";

export const App: React.FC = () => {
  // Session & Connection states
  const [sessionId, setSessionId] = useState<string>("");
  const [isPending, startTransition] = useTransition();
  const [messages, setMessages] = useState<Message[]>([]);
  const [forceMock, setForceMock] = useState<boolean>(false); // Default: Live AI Pipeline

  // History state
  const [history, setHistory] = useState<ChatSession[]>([]);

  // Inspector & UI Layout Toggles
  const [devMode, setDevMode] = useState<boolean>(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);

  // Health Diagnostics Telemetry
  const [health, setHealth] = useState<SystemHealth>({
    status: "unhealthy",
    faiss: "error",
    gemini: "error",
    memory: "error",
  });

  const auditHealth = async () => {
    const h = await checkApiHealth();
    setHealth(h);
  };

  // Periodic health pings (every 5 seconds)
  useEffect(() => {
    auditHealth();
    const interval = setInterval(auditHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  // Load history from localStorage on boot
  useEffect(() => {
    const savedHistory = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setHistory(parsed);
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
    handleCreateNewSession();
  }, []);

  // Save current messages to history when they change
  useEffect(() => {
    if (messages.length > 0 && sessionId) {
      setHistory(prev => {
        const existingSessionIndex = prev.findIndex(s => s.id === sessionId);
        
        // Generate title from first user message
        const firstUserMsg = messages.find(m => m.role === "user");
        const title = firstUserMsg 
          ? (firstUserMsg.content.length > 30 ? firstUserMsg.content.substring(0, 30) + "..." : firstUserMsg.content)
          : "New Conversation";

        const newSession: ChatSession = {
          id: sessionId,
          title,
          date: new Date().toISOString(),
          messages: [...messages]
        };

        let updated;
        if (existingSessionIndex >= 0) {
          updated = [...prev];
          updated[existingSessionIndex] = newSession;
        } else {
          updated = [newSession, ...prev];
        }
        
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    }
  }, [messages, sessionId]);

  const handleCreateNewSession = async () => {
    setMessages([]);
    const id = await createSession();
    setSessionId(id);
    setIsHistoryOpen(false);
  };

  const handleClearSession = async () => {
    if (sessionId) await deleteSession(sessionId);
    handleCreateNewSession();
  };

  const loadSession = (session: ChatSession) => {
    setSessionId(session.id);
    setMessages(session.messages);
    setIsHistoryOpen(false);
  };

  const deleteHistorySession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setHistory(prev => {
      const updated = prev.filter(s => s.id !== id);
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
    if (id === sessionId) {
      handleCreateNewSession();
    }
  };

  const handleNewMessage = (text: string) => {
    const userTurn: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    };
    setMessages((prev) => [...prev, userTurn]);

    startTransition(async () => {
      try {
        const assistantTurn = await submitChatTurn(text, sessionId, forceMock);
        setMessages((prev) => [...prev, assistantTurn]);
      } catch (err) {
        console.error("Failed to submit stateful turn", err);
      }
    });
  };

  const handleExportPDF = async () => {
    const input = document.getElementById("pdf-export-area");
    if (!input) return;

    try {
      const canvas = await html2canvas(input, {
        backgroundColor: "#111113",
        scale: 2, // Higher resolution
        useCORS: true,
      } as any);

      const imgData = canvas.toDataURL("image/png");
      
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4"
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      
      pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
      pdf.save(`StayChat_Transcript_${new Date().toISOString().split("T")[0]}.pdf`);
    } catch (err) {
      console.error("Failed to export PDF", err);
    }
  };

  const activeTelemetry = messages[messages.length - 1]?.telemetry;
  const isOnline = health.status === "healthy";

  return (
    <div className="min-h-screen bg-[#111113] text-zinc-100 flex flex-col font-sans antialiased overflow-hidden relative selection:bg-amber-500/30 selection:text-amber-200">
      
      {/* Subtle Ambient Glow */}
      <div className="absolute top-0 inset-x-0 h-[500px] bg-gradient-to-b from-amber-500/5 to-transparent pointer-events-none" aria-hidden="true" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" aria-hidden="true" />
      
      {/* ============================================================
          TOP HEADER — Premium SaaS Navigation
          ============================================================ */}
      <header className="flex-none h-16 border-b border-zinc-800/50 bg-[#111113]/80 backdrop-blur-md px-4 lg:px-6 flex items-center justify-between z-40 relative">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setIsHistoryOpen(true)}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/80 rounded-md transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
          
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-gradient-to-br from-amber-500/20 to-amber-600/5 border border-amber-500/20 flex items-center justify-center shadow-glow-amber">
              <Hotel className="h-4 w-4 text-amber-400" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-[13px] font-bold tracking-wide text-zinc-100">StayChat AI</h1>
              <p className="text-[10px] text-zinc-500 font-medium hidden sm:block">Grand Hotel Concierge</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4">
          {/* Export PDF Button */}
          <button
            onClick={handleExportPDF}
            disabled={messages.length === 0}
            className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800/50 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 rounded-md text-xs font-medium border border-zinc-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="h-3.5 w-3.5" />
            Export PDF
          </button>

          {/* New Chat Button */}
          <button
            onClick={handleClearSession}
            className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800/50 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 rounded-md text-xs font-medium border border-zinc-700/50 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            New Chat
          </button>

          {/* Settings Dropdown Wrapper */}
          <div className="relative">
            <button
              onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              className="h-8 w-8 flex items-center justify-center rounded-full hover:bg-zinc-800/80 text-zinc-400 hover:text-zinc-100 transition-colors"
            >
              <Settings className="h-4 w-4" />
            </button>

            {/* Floating Settings Menu */}
            {isSettingsOpen && (
              <div className="absolute right-0 top-10 w-64 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl p-4 flex flex-col gap-4 z-50 animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-2 border-b border-zinc-800 pb-2">
                  <span>SYSTEM STATUS</span>
                  <span className={`flex items-center gap-1.5 font-semibold ${isOnline ? "text-emerald-400" : "text-amber-500"}`}>
                    {isOnline ? <Wifi className="h-3 w-3 animate-pulse" /> : <WifiOff className="h-3 w-3" />}
                    {isOnline ? "ONLINE" : "OFFLINE"}
                  </span>
                </div>

                {/* Toggle 1: Live AI Concierge */}
                <div className="flex justify-between items-center group">
                  <div className="flex items-center gap-2.5">
                    <RefreshCw className={`h-4 w-4 text-zinc-500 ${!forceMock && isOnline ? "animate-spin text-emerald-400" : ""}`} />
                    <div className="flex flex-col">
                      <p className="text-[12px] text-zinc-200 font-medium leading-none">Live AI Pipeline</p>
                      <p className="text-[10px] text-zinc-500 mt-1">
                        {forceMock ? "Using local simulator" : "Using Gemini backend"}
                      </p>
                    </div>
                  </div>
                  <button
                    role="switch"
                    aria-checked={!forceMock}
                    onClick={() => setForceMock(!forceMock)}
                    className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${!forceMock ? "bg-emerald-500" : "bg-zinc-700"}`}
                  >
                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${!forceMock ? "translate-x-3.5" : "translate-x-0.5"}`} />
                  </button>
                </div>

                {/* Toggle 2: Developer Inspector */}
                <div className="flex justify-between items-center group">
                  <div className="flex items-center gap-2.5">
                    <ShieldAlert className={`h-4 w-4 ${devMode ? "text-indigo-400" : "text-zinc-500"}`} />
                    <div className="flex flex-col">
                      <p className="text-[12px] text-zinc-200 font-medium leading-none">Dev Inspector</p>
                      <p className="text-[10px] text-zinc-500 mt-1">Show RAG telemetry</p>
                    </div>
                  </div>
                  <button
                    role="switch"
                    aria-checked={devMode}
                    onClick={() => {
                      const next = !devMode;
                      setDevMode(next);
                      setIsInspectorOpen(next);
                    }}
                    className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${devMode ? "bg-indigo-500" : "bg-zinc-700"}`}
                  >
                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${devMode ? "translate-x-3.5" : "translate-x-0.5"}`} />
                  </button>
                </div>
              </div>
            )}
          </div>

          <button className="h-8 w-8 flex items-center justify-center rounded-full bg-zinc-800 text-zinc-300 ml-1">
            <UserCircle className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* ============================================================
          MAIN CHAT AREA — Centered SaaS Layout
          ============================================================ */}
      <main className="flex-1 overflow-hidden flex justify-center relative z-10 w-full" onClick={() => isSettingsOpen && setIsSettingsOpen(false)}>
        <div className="w-full max-w-3xl h-full flex flex-col relative px-4 md:px-0">
          <ChatConsole
            messages={messages}
            isPending={isPending}
            onSendMessage={handleNewMessage}
            devMode={devMode}
            onOpenInspector={() => setIsInspectorOpen(true)}
            forceMock={forceMock}
            isOnline={isOnline}
          />
        </div>
      </main>

      {/* ============================================================
          HISTORY SLIDE-OUT DRAWER
          ============================================================ */}
      {isHistoryOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in"
            onClick={() => setIsHistoryOpen(false)}
          />
          
          {/* Drawer */}
          <div className="relative w-80 max-w-[80vw] h-full bg-[#0c0c0f] border-r border-zinc-800/80 shadow-2xl flex flex-col animate-in slide-in-from-left duration-300">
            <div className="p-4 border-b border-zinc-800/60 flex items-center justify-between">
              <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-widest">Chat History</h2>
              <button 
                onClick={() => setIsHistoryOpen(false)}
                className="p-1 text-zinc-500 hover:text-zinc-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="p-4">
              <button
                onClick={handleClearSession}
                className="w-full py-2.5 bg-zinc-800/50 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/50 rounded-xl flex items-center justify-center gap-2 transition-all font-semibold text-xs mb-6"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                New Conversation
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1 custom-scrollbar">
              {history.length === 0 ? (
                <div className="text-center text-zinc-500 text-xs py-10">
                  No previous chats found.
                </div>
              ) : (
                history.map(session => (
                  <div 
                    key={session.id}
                    onClick={() => loadSession(session)}
                    className={`w-full text-left p-3 rounded-xl hover:bg-zinc-800/60 transition-colors cursor-pointer group flex justify-between items-center ${sessionId === session.id ? 'bg-zinc-800/80 border border-zinc-700/50' : 'border border-transparent'}`}
                  >
                    <div className="flex items-start gap-3 overflow-hidden">
                      <MessageSquare className="h-4 w-4 text-zinc-500 mt-0.5 flex-shrink-0" />
                      <div className="flex flex-col overflow-hidden">
                        <span className="text-[13px] text-zinc-200 font-medium truncate leading-tight">
                          {session.title}
                        </span>
                        <span className="text-[10px] text-zinc-500 flex items-center gap-1 mt-1">
                          <Clock className="h-2.5 w-2.5" />
                          {new Date(session.date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button 
                      onClick={(e) => deleteHistorySession(e, session.id)}
                      className="p-1.5 text-zinc-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================
          DEVELOPER INSPECTOR SLIDE-OUT DRAWER
          ============================================================ */}
      <InspectorDrawer
        telemetry={activeTelemetry}
        isOpen={devMode && isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
      />
    </div>
  );
};

export default App;
