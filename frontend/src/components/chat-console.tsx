import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, Headset, Sparkles } from "lucide-react";
import { Message } from "../types";
import { cn } from "../services/cn";
interface ChatConsoleProps {
  messages: Message[];
  isPending: boolean;
  onSendMessage: (text: string) => void;
  devMode?: boolean;
  onOpenInspector?: () => void;
  forceMock?: boolean;
  isOnline?: boolean;
}

// ==============================================================================
// RICH TEXT RENDERER — Parses markdown-lite, prices, phones, emails
// ==============================================================================
const renderFormattedContent = (content: string): React.ReactNode => {
  if (!content) return null;

  const lines = content.split("\n");

  return (
    <div className="space-y-1.5 text-zinc-200">
      {lines.map((line, lineIdx) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={lineIdx} className="h-1" />;
        }

        const isBullet = trimmed.startsWith("* ") || trimmed.startsWith("- ");
        const isNumbered = /^\d+\.\s/.test(trimmed);

        let displayContent = trimmed;
        if (isBullet) displayContent = trimmed.substring(2);
        else if (isNumbered) displayContent = trimmed.replace(/^\d+\.\s/, "");

        // Inline parser: bold (**text**) + entity tokens (₹, +91, @email)
        const parseInline = (text: string, keyPrefix: string): React.ReactNode[] => {
          const parts: React.ReactNode[] = [];
          const boldRegex = /\*\*([^*]+)\*\*/g;
          let lastIdx = 0;
          let match;
          let boldIdx = 0;

          const styleEntities = (raw: string, pKey: string): React.ReactNode[] => {
            const sub: React.ReactNode[] = [];
            // Matches: ₹4,500/night  |  +91-22-5555-1234  |  user@email.com
            const entityRx = /(₹[\d,]+(?:\/\w+)?|\+?[\d][\d\-\s]{6,16}|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})/g;
            let sLast = 0;
            let sm;
            while ((sm = entityRx.exec(raw)) !== null) {
              if (sm.index > sLast) sub.push(raw.substring(sLast, sm.index));
              const val = sm[0];
              const isPrice = val.startsWith("₹");
              const isEmail = val.includes("@");
              if (isPrice) {
                sub.push(
                  <span key={`${pKey}-p-${sm.index}`} className="price-token">
                    {val}
                  </span>
                );
              } else if (isEmail) {
                sub.push(
                  <a key={`${pKey}-e-${sm.index}`} href={`mailto:${val}`}
                    className="text-sky-400 hover:text-sky-300 underline underline-offset-2 transition-colors font-medium">
                    {val}
                  </a>
                );
              } else {
                sub.push(
                  <span key={`${pKey}-ph-${sm.index}`} className="phone-token">
                    {val}
                  </span>
                );
              }
              sLast = entityRx.lastIndex;
            }
            if (sLast < raw.length) sub.push(raw.substring(sLast));
            return sub;
          };

          while ((match = boldRegex.exec(text)) !== null) {
            if (match.index > lastIdx) {
              parts.push(...styleEntities(text.substring(lastIdx, match.index), `${keyPrefix}-pre-${boldIdx}`));
            }
            parts.push(
              <strong key={`${keyPrefix}-b-${boldIdx}`}
                className="font-semibold text-zinc-100">
                {styleEntities(match[1], `${keyPrefix}-bsub-${boldIdx}`)}
              </strong>
            );
            lastIdx = boldRegex.lastIndex;
            boldIdx++;
          }
          if (lastIdx < text.length) {
            parts.push(...styleEntities(text.substring(lastIdx), `${keyPrefix}-end`));
          }
          return parts;
        };

        const inlineParsed = parseInline(displayContent, `l${lineIdx}`);

        if (isBullet) {
          return (
            <div key={lineIdx} className="flex items-start gap-2.5 pl-1 animate-fade-in">
              <span className="text-amber-400 mt-1 flex-shrink-0 text-[11px]">✦</span>
              <span className="leading-relaxed text-[12.5px] md:text-[13px]">{inlineParsed}</span>
            </div>
          );
        }

        if (isNumbered) {
          const numPrefix = trimmed.match(/^\d+/)?.[0] || "1";
          return (
            <div key={lineIdx} className="flex items-start gap-2.5 pl-1 animate-fade-in">
              <span className="flex-shrink-0 mt-0.5 h-5 w-5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300 font-bold font-mono text-[9px] flex items-center justify-center">
                {numPrefix}
              </span>
              <span className="leading-relaxed text-[12.5px] md:text-[13px]">{inlineParsed}</span>
            </div>
          );
        }

        return (
          <p key={lineIdx} className="leading-relaxed text-[12.5px] md:text-[13px] animate-fade-in">
            {inlineParsed}
          </p>
        );
      })}
    </div>
  );
};

// ==============================================================================
// MAIN CHAT CONSOLE COMPONENT
// ==============================================================================
export const ChatConsole: React.FC<ChatConsoleProps> = ({
  messages,
  isPending,
  onSendMessage,
}) => {
  const [inputText, setInputText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isPending) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  const suggestions = [
    { text: "What time does the pool close?", icon: "🏊", desc: "Amenities & Timings" },
    { text: "Do you have Executive Suites?", icon: "🛏️", desc: "Rooms & Pricing" },
    { text: "What are breakfast timings?", icon: "🍽️", desc: "Dining Options" },
    { text: "Is airport transfer available?", icon: "🚕", desc: "Transportation" },
  ];

  return (
    <div className="flex flex-col w-full h-[calc(100vh-64px)] relative">
      
      {/* ====================================================================
          SCROLLABLE MESSAGE VIEWPORT
          ==================================================================== */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 pt-10 pb-36 space-y-8"
        style={{ scrollbarGutter: "stable" }}
      >
        {messages.length === 0 ? (
          /* ══════════════════════ EMPTY STATE / HERO ══════════════════════ */
          <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto text-center space-y-10 animate-in fade-in zoom-in duration-500">
            <div className="flex flex-col items-center space-y-4">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/5 border border-amber-500/20 flex items-center justify-center shadow-glow-amber">
                <Bot className="h-8 w-8 text-amber-400" />
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight text-zinc-100 mb-2">How can I help you today?</h1>
                <p className="text-[14px] text-zinc-400 max-w-sm mx-auto">
                  Your AI concierge is ready. Ask about your stay, room upgrades, dining, or local transport.
                </p>
              </div>
            </div>

            {/* Premium Suggestion Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full text-left">
              {suggestions.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => !isPending && onSendMessage(sug.text)}
                  className="p-4 bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-800/60 hover:border-zinc-700 rounded-2xl transition-all duration-300 flex flex-col gap-2 group hover:shadow-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg bg-zinc-800/80 p-1.5 rounded-lg border border-zinc-700/50 group-hover:bg-zinc-700 transition-colors">
                      {sug.icon}
                    </span>
                    <span className="text-[11px] font-mono font-medium text-zinc-500 uppercase tracking-widest">{sug.desc}</span>
                  </div>
                  <span className="text-sm font-medium text-zinc-200 leading-snug group-hover:text-amber-400 transition-colors">{sug.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ══════════════════════ MESSAGE TRANSCRIPT ══════════════════════ */
          <div id="pdf-export-area" className="max-w-3xl mx-auto w-full space-y-8 pb-10">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const escalated = msg.telemetry?.escalation_status === "escalated";

              return (
                <div key={msg.id} className="w-full flex flex-col animate-in fade-in slide-in-from-bottom-2">
                  <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
                    
                    {/* Assistant Message Layout */}
                    {!isUser && (
                      <div className="flex gap-4 max-w-[90%]">
                        <div className="flex-shrink-0 h-8 w-8 mt-1 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/30 flex items-center justify-center">
                          <Sparkles className="h-4 w-4 text-amber-400" />
                        </div>
                        <div className="flex-1 flex flex-col mt-1.5">
                          {renderFormattedContent(msg.content)}
                          
                          {/* Escalation Block */}
                          {escalated && (
                            <div className="mt-4 rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border bg-amber-950/20 border-amber-500/20 shadow-glow-amber">
                              <div className="flex items-center gap-3">
                                <Headset className="h-5 w-5 text-amber-400 animate-pulse" />
                                <div>
                                  <h4 className="text-[13px] font-semibold text-zinc-200">Connecting to Human Concierge</h4>
                                  <p className="text-[11px] text-zinc-400 mt-0.5">Vikram S. is reviewing your request...</p>
                                </div>
                              </div>
                              <button className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold text-[11px] uppercase tracking-wider rounded-lg transition-all shadow-glow-amber">
                                Connect Live
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* User Message Layout */}
                    {isUser && (
                      <div className="max-w-[80%] bg-zinc-800 text-zinc-100 rounded-3xl rounded-tr-sm px-5 py-3 text-[14px] leading-relaxed shadow-md">
                        {msg.content}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            
            {/* Typing Indicator */}
            {isPending && (
              <div className="flex gap-4 max-w-[90%] w-full animate-in fade-in">
                <div className="flex-shrink-0 h-8 w-8 mt-1 rounded-full bg-gradient-to-br from-amber-500/10 to-amber-600/5 border border-amber-500/20 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-amber-400/50 animate-pulse" />
                </div>
                <div className="flex-1 mt-3">
                  <div className="dot-flashing" />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ====================================================================
          FLOATING INPUT AREA
          ==================================================================== */}
      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-[#111113] via-[#111113] to-transparent pt-10 pb-6 px-4 pointer-events-none">
        <div className="max-w-3xl mx-auto w-full pointer-events-auto">
          <form 
            onSubmit={handleSubmit} 
            className="relative flex items-center w-full bg-zinc-900/80 backdrop-blur-xl border border-zinc-700/50 rounded-2xl p-2 shadow-2xl focus-within:border-amber-500/50 focus-within:ring-1 focus-within:ring-amber-500/50 transition-all"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Message StayChat AI..."
              disabled={isPending}
              className="flex-1 bg-transparent border-none px-4 py-3 text-[15px] text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-0 font-sans disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isPending}
              className="flex-shrink-0 h-10 w-10 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-zinc-950 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 disabled:bg-zinc-700 disabled:text-zinc-500 disabled:cursor-not-allowed shadow-glow-amber"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          
          <p className="text-[10px] text-zinc-600 font-medium text-center mt-3">
            StayChat AI can make mistakes. Please verify important information with the front desk.
          </p>
        </div>
      </div>
    </div>
  );
};

