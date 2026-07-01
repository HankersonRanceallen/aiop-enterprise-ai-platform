"use client";
import { useState, useRef, useCallback } from "react";
import {
  Brain, Search, BarChart2, FileText,
  Play, Loader2, CheckCircle, AlertCircle, ChevronDown, ChevronUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import Sidebar from "@/components/Sidebar";
import Cookies from "js-cookie";

// ─── Types ────────────────────────────────────────────────────────────────────
interface StepEvent {
  type: "step_done";
  agent: string;
  label: string;
  emoji: string;
  status: "done" | "failed";
  message: string;
  output?: any;
  latency_ms: number;
}

interface CompleteEvent {
  type: "complete";
  report: string;
  step_log: StepEvent[];
  total_tokens: number;
  total_latency_ms: number;
}

type AgentEvent = { type: "started" } | StepEvent | CompleteEvent | { type: "error"; message: string };

type RunStatus = "idle" | "running" | "complete" | "error";

// ─── Agent metadata ───────────────────────────────────────────────────────────
const AGENTS: { key: string; label: string; icon: React.ElementType; color: string }[] = [
  { key: "planner",   label: "Planner Agent",   icon: Brain,     color: "text-violet-600 bg-violet-50" },
  { key: "retriever", label: "Retriever Agent",  icon: Search,    color: "text-blue-600 bg-blue-50" },
  { key: "analysis",  label: "Analysis Agent",   icon: BarChart2, color: "text-amber-600 bg-amber-50" },
  { key: "report",    label: "Report Agent",     icon: FileText,  color: "text-emerald-600 bg-emerald-50" },
];

const EXAMPLE_TASKS = [
  "Analyze all uploaded documents and generate an executive summary report",
  "What are the key risks and recommendations across all documents?",
  "Compare and contrast the main topics covered in the uploaded documents",
  "Extract all action items and deadlines mentioned across documents",
];

// ─── Step card ────────────────────────────────────────────────────────────────
function StepCard({ step, isActive }: { step: StepEvent; isActive: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const meta = AGENTS.find((a) => a.key === step.agent);
  const Icon = meta?.icon || Brain;

  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${
      isActive ? "border-primary-200 shadow-sm" : "border-gray-100"
    }`}>
      <div
        className="flex items-center gap-3 px-4 py-3 bg-white cursor-pointer"
        onClick={() => step.output && setExpanded(!expanded)}
      >
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${meta?.color || "text-gray-500 bg-gray-50"}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{meta?.label || step.agent}</p>
          <p className="text-xs text-gray-400 truncate">{step.message}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-300">{step.latency_ms.toFixed(0)}ms</span>
          <CheckCircle className="w-4 h-4 text-emerald-500" />
          {step.output && (
            expanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />
          )}
        </div>
      </div>
      {expanded && step.output && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-600">
          <pre className="whitespace-pre-wrap font-mono">
            {typeof step.output === "string"
              ? step.output
              : JSON.stringify(step.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── Active step indicator ────────────────────────────────────────────────────
function ActiveStep({ agentKey }: { agentKey: string }) {
  const meta = AGENTS.find((a) => a.key === agentKey);
  const Icon = meta?.icon || Brain;

  return (
    <div className="border border-primary-100 rounded-xl bg-primary-50/50 px-4 py-3 flex items-center gap-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${meta?.color || ""}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-800">{meta?.label || agentKey}</p>
        <p className="text-xs text-gray-400">Running…</p>
      </div>
      <Loader2 className="w-4 h-4 text-primary-500 animate-spin flex-shrink-0" />
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function AgentsPage() {
  const [task, setTask] = useState("");
  const [status, setStatus] = useState<RunStatus>("idle");
  const [completedSteps, setCompletedSteps] = useState<StepEvent[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [result, setResult] = useState<CompleteEvent | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const runAgents = useCallback(async () => {
    if (!task.trim() || status === "running") return;

    setStatus("running");
    setCompletedSteps([]);
    setActiveAgent("planner");
    setResult(null);
    setErrorMsg("");

    const token = Cookies.get("access_token");
    abortRef.current = new AbortController();

    try {
      const response = await fetch("/api/v1/agents/run/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ task }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: AgentEvent = JSON.parse(line.slice(6));

            if (event.type === "started") {
              setActiveAgent("planner");
            } else if (event.type === "step_done") {
              setCompletedSteps((prev) => [...prev, event as StepEvent]);
              // Set next active agent
              const agentKeys = AGENTS.map((a) => a.key);
              const idx = agentKeys.indexOf(event.agent);
              setActiveAgent(idx < agentKeys.length - 1 ? agentKeys[idx + 1] : null);
            } else if (event.type === "complete") {
              setResult(event as CompleteEvent);
              setActiveAgent(null);
              setStatus("complete");
            } else if (event.type === "error") {
              setErrorMsg((event as any).message);
              setStatus("error");
              setActiveAgent(null);
            }
          } catch {
            // Ignore parse errors on incomplete chunks
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setErrorMsg(err.message || "Something went wrong");
        setStatus("error");
      }
    } finally {
      setActiveAgent(null);
      if (status === "running") setStatus("idle");
    }
  }, [task, status]);

  function reset() {
    abortRef.current?.abort();
    setStatus("idle");
    setCompletedSteps([]);
    setActiveAgent(null);
    setResult(null);
    setErrorMsg("");
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 flex overflow-hidden">

        {/* Left panel - input + step trace */}
        <div className="w-96 flex-shrink-0 border-r border-gray-100 flex flex-col bg-white">
          <div className="px-5 py-5 border-b border-gray-100">
            <h1 className="font-semibold text-gray-900">Agent Workflows</h1>
            <p className="text-xs text-gray-400 mt-0.5">Multi-agent document analysis</p>
          </div>

          {/* Task input */}
          <div className="px-5 py-4 border-b border-gray-100">
            <label className="block text-xs font-medium text-gray-600 mb-2">Task</label>
            <textarea
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
              placeholder="Analyze all documents and generate a summary report…"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              disabled={status === "running"}
            />

            {/* Example tasks */}
            <div className="mt-2 space-y-1">
              {EXAMPLE_TASKS.slice(0, 2).map((t, i) => (
                <button
                  key={i}
                  onClick={() => setTask(t)}
                  className="text-xs text-primary-500 hover:underline text-left block"
                >
                  → {t}
                </button>
              ))}
            </div>

            <div className="flex gap-2 mt-3">
              <button
                onClick={runAgents}
                disabled={!task.trim() || status === "running"}
                className="flex-1 btn-primary flex items-center justify-center gap-2 text-sm"
              >
                {status === "running" ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Running…</>
                ) : (
                  <><Play className="w-3.5 h-3.5" /> Run agents</>
                )}
              </button>
              {status !== "idle" && (
                <button onClick={reset} className="btn-ghost text-sm">Reset</button>
              )}
            </div>
          </div>

          {/* Agent pipeline + steps */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2">
            {status === "idle" && completedSteps.length === 0 && (
              <div className="text-center py-8">
                <div className="flex justify-center gap-3 mb-4">
                  {AGENTS.map(({ key, icon: Icon, color }) => (
                    <div key={key} className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                  ))}
                </div>
                <p className="text-sm text-gray-400">
                  4 agents collaborate to analyze<br />your documents end-to-end
                </p>
              </div>
            )}

            {completedSteps.map((step, i) => (
              <StepCard key={i} step={step} isActive={false} />
            ))}

            {activeAgent && <ActiveStep agentKey={activeAgent} />}

            {status === "error" && (
              <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{errorMsg || "Agent run failed"}</span>
              </div>
            )}

            {result && (
              <div className="flex items-center gap-2 text-xs text-gray-400 pt-2 border-t border-gray-100">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                Completed in {(result.total_latency_ms / 1000).toFixed(1)}s
                · {result.total_tokens.toLocaleString()} tokens
              </div>
            )}
          </div>
        </div>

        {/* Right panel - report output */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {!result ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-sm px-8">
                <FileText className="w-12 h-12 text-gray-200 mx-auto mb-4" />
                <p className="text-sm font-medium text-gray-500">Report will appear here</p>
                <p className="text-xs text-gray-400 mt-1">
                  Enter a task and run the agents. The final report will be displayed as it's generated.
                </p>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-8 py-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Generated Report</h2>
                  <p className="text-sm text-gray-400 mt-0.5 line-clamp-1">{task}</p>
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(result.report)}
                  className="btn-ghost text-sm"
                >
                  Copy
                </button>
              </div>
              <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-6">
                <ReactMarkdown className="prose prose-sm max-w-none prose-headings:font-semibold prose-headings:text-gray-800 prose-p:text-gray-600">
                  {result.report}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
