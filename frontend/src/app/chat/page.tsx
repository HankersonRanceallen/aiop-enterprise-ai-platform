"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, FileText, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import Sidebar from "@/components/Sidebar";
import { chatApi } from "@/lib/api";

interface Source {
  document_id: number;
  document_title: string;
  chunk_index: number;
  content: string;
  score: number;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  llm_model?: string;
  latency_ms?: number;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | undefined>();
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await chatApi.send(text, conversationId);
      setConversationId(data.conversation_id);
      const assistantMsg: Message = {
        id: data.message_id,
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        llm_model: data.llm_model,
        latency_ms: data.latency_ms,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: err.response?.data?.detail || "Something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function toggleSources(msgId: number) {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  }

  return (
    <div className="flex h-screen">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 bg-white flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-gray-900">AI Assistant</h1>
            <p className="text-xs text-gray-400">Ask questions about your documents</p>
          </div>
          {conversationId && (
            <span className="text-xs text-gray-400">Conversation #{conversationId}</span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mb-4">
                <Bot className="w-8 h-8 text-primary-600" />
              </div>
              <h2 className="text-lg font-medium text-gray-800 mb-1">Ask anything</h2>
              <p className="text-sm text-gray-400 max-w-sm">
                I'll search through your uploaded documents and answer with cited sources.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              {/* Avatar */}
              <div
                className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5 ${
                  msg.role === "user"
                    ? "bg-primary-600"
                    : "bg-gray-100"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="w-3.5 h-3.5 text-white" />
                ) : (
                  <Bot className="w-3.5 h-3.5 text-gray-500" />
                )}
              </div>

              {/* Bubble */}
              <div className={`max-w-2xl ${msg.role === "user" ? "items-end" : ""} flex flex-col`}>
                <div
                  className={`rounded-2xl px-4 py-3 text-sm ${
                    msg.role === "user"
                      ? "bg-primary-600 text-white rounded-tr-sm"
                      : "bg-white border border-gray-100 shadow-sm rounded-tl-sm text-gray-800"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <ReactMarkdown className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1">
                      {msg.content}
                    </ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 w-full">
                    <button
                      onClick={() => toggleSources(msg.id)}
                      className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600"
                    >
                      <FileText className="w-3 h-3" />
                      {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                      <span>{expandedSources.has(msg.id) ? "▲" : "▼"}</span>
                    </button>

                    {expandedSources.has(msg.id) && (
                      <div className="mt-2 space-y-2">
                        {msg.sources.map((src, i) => (
                          <div
                            key={i}
                            className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-gray-700">
                                {src.document_title}
                              </span>
                              <span className="text-xs text-gray-400">
                                {(src.score * 100).toFixed(0)}% match
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 line-clamp-2">{src.content}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Meta */}
                {msg.llm_model && (
                  <p className="text-xs text-gray-300 mt-1">
                    {msg.llm_model} · {msg.latency_ms?.toFixed(0)}ms
                  </p>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-gray-400" />
              </div>
              <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm px-4 py-3">
                <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-gray-100 bg-white">
          <div className="flex gap-3 items-end">
            <textarea
              className="input flex-1 resize-none min-h-[44px] max-h-32"
              placeholder="Ask a question about your documents…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              rows={1}
            />
            <button
              className="btn-primary flex-shrink-0 h-11 w-11 flex items-center justify-center rounded-xl"
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-300 mt-2">Enter to send · Shift+Enter for new line</p>
        </div>
      </main>
    </div>
  );
}
