"use client";
import { useState, useEffect } from "react";
import {
  FlaskConical, ExternalLink, Loader2, CheckCircle,
  TrendingUp, Zap, DollarSign, Clock, AlertTriangle,
  BarChart2, RefreshCw,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { dashboardApi } from "@/lib/api";
import api from "@/lib/api";
import ReactMarkdown from "react-markdown";

// ─── Types ────────────────────────────────────────────────────────────────────
interface ModelRow {
  model: string;
  provider: string;
  total_queries: number;
  avg_faithfulness: number;
  avg_relevance: number;
  avg_completeness: number;
  avg_composite: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
  total_tokens: number;
}

interface EvalResult {
  id: number;
  question: string;
  llm_model: string;
  llm_provider: string;
  faithfulness: number;
  relevance: number;
  completeness: number;
  composite_score: number;
  reasoning: Record<string, string> | null;
  created_at: string;
}

interface Monitoring {
  period_hours: number;
  total_requests: number;
  rag_requests: number;
  agent_requests: number;
  error_count: number;
  avg_latency_ms: number;
  total_tokens: number;
  estimated_cost_usd: number;
  top_models: { model: string; provider: string; queries: number; avg_latency_ms: number }[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 85 ? "text-emerald-700 bg-emerald-50 border-emerald-200" :
    pct >= 70 ? "text-amber-700 bg-amber-50 border-amber-200" :
                "text-red-700 bg-red-50 border-red-200";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium border ${color}`}>
      {pct}%
    </span>
  );
}

function ScoreBar({ score, color = "bg-primary-500" }: { score: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score * 100}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{Math.round(score * 100)}%</span>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub, iconColor = "text-primary-600", iconBg = "bg-primary-50" }: any) {
  return (
    <div className="card flex items-start gap-3">
      <div className={`w-9 h-9 rounded-xl ${iconBg} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <div>
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-xl font-semibold text-gray-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Evaluate form ────────────────────────────────────────────────────────────
function EvaluateForm({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState({ question: "", answer: "" });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);

  async function submit() {
    if (!form.question || !form.answer) return;
    setLoading(true);
    try {
      const { data } = await api.post("/mlops/evaluate", {
        question: form.question,
        answer: form.answer,
        retrieved_chunks: [],
      });
      setResult(data);
      onDone();
    } finally {
      setLoading(false);
    }
  }

  if (result) return (
    <div className="card border-emerald-100">
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-gray-800">Evaluation complete</span>
        <span className="ml-auto text-xs text-gray-400">{result.llm_model}</span>
      </div>
      <div className="space-y-3">
        {[
          { label: "Faithfulness", score: result.faithfulness, color: "bg-violet-500" },
          { label: "Relevance",    score: result.relevance,    color: "bg-blue-500" },
          { label: "Completeness", score: result.completeness, color: "bg-emerald-500" },
        ].map(({ label, score, color }) => (
          <div key={label}>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{label}</span>
              <ScoreBadge score={score} />
            </div>
            <ScoreBar score={score} color={color} />
          </div>
        ))}
        <div className="pt-2 border-t border-gray-100">
          <div className="flex justify-between text-xs font-medium text-gray-700">
            <span>Composite score</span>
            <ScoreBadge score={result.composite_score} />
          </div>
        </div>
      </div>
      <button onClick={() => setResult(null)} className="btn-ghost text-xs mt-4">Run another</button>
    </div>
  );

  return (
    <div className="card">
      <p className="text-sm font-medium text-gray-700 mb-3">Run evaluation</p>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Question</label>
          <input className="input text-sm" placeholder="What is the return policy?" value={form.question}
            onChange={e => setForm({ ...form, question: e.target.value })} />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Answer to evaluate</label>
          <textarea className="input text-sm resize-none" rows={3} placeholder="The return policy allows…"
            value={form.answer} onChange={e => setForm({ ...form, answer: e.target.value })} />
        </div>
        <button onClick={submit} disabled={loading || !form.question || !form.answer} className="btn-primary w-full text-sm">
          {loading ? <><Loader2 className="w-3.5 h-3.5 animate-spin inline mr-2" />Evaluating…</> : "Evaluate with LLM judge"}
        </button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type Tab = "comparison" | "evaluations" | "monitoring";

export default function MLOpsPage() {
  const [tab, setTab] = useState<Tab>("comparison");
  const [comparison, setComparison] = useState<ModelRow[]>([]);
  const [evaluations, setEvaluations] = useState<EvalResult[]>([]);
  const [monitoring, setMonitoring] = useState<Monitoring | null>(null);
  const [mlflowUrl, setMlflowUrl] = useState("http://localhost:5001");
  const [loading, setLoading] = useState(true);
  const [expandedEval, setExpandedEval] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [cmp, evals, mon, mf] = await Promise.allSettled([
        api.get("/mlops/model-comparison"),
        api.get("/mlops/evaluations?limit=20"),
        api.get("/mlops/monitoring?hours=24"),
        api.get("/mlops/mlflow-url"),
      ]);
      if (cmp.status === "fulfilled") setComparison(cmp.value.data);
      if (evals.status === "fulfilled") setEvaluations(evals.value.data);
      if (mon.status === "fulfilled") setMonitoring(mon.value.data);
      if (mf.status === "fulfilled") setMlflowUrl(mf.value.data.url);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const tabs: { key: Tab; label: string }[] = [
    { key: "comparison",  label: "Model comparison" },
    { key: "evaluations", label: "Evaluations" },
    { key: "monitoring",  label: "Monitoring" },
  ];

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-5xl mx-auto px-8 py-6">

          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <FlaskConical className="w-5 h-5 text-violet-600" />
                <h1 className="text-xl font-semibold text-gray-900">MLOps</h1>
              </div>
              <p className="text-sm text-gray-400">Experiment tracking, evaluation, and monitoring</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={load} className="btn-ghost text-sm flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
              <a href={mlflowUrl} target="_blank" rel="noopener noreferrer"
                className="btn-primary text-sm flex items-center gap-1.5">
                <ExternalLink className="w-3.5 h-3.5" /> MLflow UI
              </a>
            </div>
          </div>

          {/* Monitoring stat pills */}
          {monitoring && (
            <div className="grid grid-cols-4 gap-3 mb-6">
              <StatCard icon={TrendingUp} label="Requests (24h)" value={monitoring.total_requests}
                sub={`${monitoring.rag_requests} RAG · ${monitoring.agent_requests} agent`}
                iconColor="text-blue-600" iconBg="bg-blue-50" />
              <StatCard icon={Clock} label="Avg latency" value={`${monitoring.avg_latency_ms.toFixed(0)}ms`}
                iconColor="text-amber-600" iconBg="bg-amber-50" />
              <StatCard icon={Zap} label="Tokens used" value={monitoring.total_tokens.toLocaleString()}
                iconColor="text-violet-600" iconBg="bg-violet-50" />
              <StatCard icon={DollarSign} label="Est. cost (24h)"
                value={`$${monitoring.estimated_cost_usd.toFixed(4)}`}
                sub={monitoring.error_count > 0 ? `${monitoring.error_count} errors` : "No errors"}
                iconColor="text-emerald-600" iconBg="bg-emerald-50" />
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-1 border-b border-gray-200 mb-6">
            {tabs.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
                  tab === t.key
                    ? "border-gray-900 text-gray-900"
                    : "border-transparent text-gray-400 hover:text-gray-600"
                }`}>
                {t.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
            </div>
          ) : (
            <>
              {/* ── Model Comparison ── */}
              {tab === "comparison" && (
                <div className="space-y-4">
                  <p className="text-xs text-gray-400">
                    Aggregated metrics across all LLM providers used in this organisation.
                    Run queries with different providers (via LLM_PROVIDER env var) to populate the table.
                  </p>
                  {comparison.length === 0 ? (
                    <div className="card text-center py-12">
                      <BarChart2 className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                      <p className="text-sm text-gray-400">No comparison data yet.</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Run queries and evaluations to populate this table.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-100">
                            {["Model", "Provider", "Queries", "Faithfulness", "Relevance", "Completeness", "Score", "Latency", "Cost / query"].map(h => (
                              <th key={h} className="text-left text-xs font-medium text-gray-400 pb-3 pr-4 whitespace-nowrap">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {comparison.map((row, i) => (
                            <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                              <td className="py-3 pr-4 font-medium text-gray-800 whitespace-nowrap">{row.model}</td>
                              <td className="py-3 pr-4 text-gray-400 capitalize">{row.provider}</td>
                              <td className="py-3 pr-4 text-gray-600">{row.total_queries}</td>
                              <td className="py-3 pr-4"><ScoreBadge score={row.avg_faithfulness} /></td>
                              <td className="py-3 pr-4"><ScoreBadge score={row.avg_relevance} /></td>
                              <td className="py-3 pr-4"><ScoreBadge score={row.avg_completeness} /></td>
                              <td className="py-3 pr-4">
                                <span className="font-semibold text-gray-900">{Math.round(row.avg_composite * 100)}%</span>
                              </td>
                              <td className="py-3 pr-4 text-gray-600">{row.avg_latency_ms.toFixed(0)}ms</td>
                              <td className="py-3 pr-4 text-gray-600">
                                {row.avg_cost_usd === 0 ? (
                                  <span className="text-emerald-600 font-medium">Free</span>
                                ) : (
                                  `$${row.avg_cost_usd.toFixed(5)}`
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* ── Evaluations ── */}
              {tab === "evaluations" && (
                <div className="grid grid-cols-5 gap-6">
                  <div className="col-span-2">
                    <EvaluateForm onDone={load} />
                  </div>
                  <div className="col-span-3 space-y-2">
                    <p className="text-xs text-gray-400 mb-3">Recent evaluations</p>
                    {evaluations.length === 0 ? (
                      <div className="card text-center py-10">
                        <p className="text-sm text-gray-400">No evaluations yet. Run one on the left.</p>
                      </div>
                    ) : evaluations.map(ev => (
                      <div key={ev.id} className="card cursor-pointer hover:border-gray-200 transition-colors"
                        onClick={() => setExpandedEval(expandedEval === ev.id ? null : ev.id)}>
                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-gray-500 truncate">{ev.question}</p>
                            <p className="text-xs text-gray-300 mt-0.5">{ev.llm_model} · {new Date(ev.created_at).toLocaleDateString()}</p>
                          </div>
                          <div className="flex gap-1.5 flex-shrink-0">
                            <ScoreBadge score={ev.faithfulness} />
                            <ScoreBadge score={ev.relevance} />
                            <ScoreBadge score={ev.completeness} />
                          </div>
                        </div>
                        {expandedEval === ev.id && ev.reasoning && (
                          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                            {Object.entries(ev.reasoning).map(([metric, reason]) => (
                              <div key={metric}>
                                <p className="text-xs font-medium text-gray-600 capitalize">{metric}</p>
                                <p className="text-xs text-gray-400">{reason}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Monitoring ── */}
              {tab === "monitoring" && monitoring && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    {/* Top models */}
                    <div className="card">
                      <p className="text-sm font-medium text-gray-700 mb-4">Top models (24h)</p>
                      {monitoring.top_models.length === 0 ? (
                        <p className="text-xs text-gray-400">No data yet</p>
                      ) : monitoring.top_models.map((m, i) => (
                        <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                          <span className="text-xs text-gray-300 w-4">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-800 truncate">{m.model}</p>
                            <p className="text-xs text-gray-400 capitalize">{m.provider}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium text-gray-900">{m.queries}</p>
                            <p className="text-xs text-gray-400">{m.avg_latency_ms.toFixed(0)}ms avg</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Error rate */}
                    <div className="card">
                      <p className="text-sm font-medium text-gray-700 mb-4">Health (24h)</p>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>Success rate</span>
                            <span>{monitoring.total_requests > 0
                              ? (((monitoring.total_requests - monitoring.error_count) / monitoring.total_requests) * 100).toFixed(1)
                              : 100}%</span>
                          </div>
                          <ScoreBar score={monitoring.total_requests > 0
                            ? (monitoring.total_requests - monitoring.error_count) / monitoring.total_requests
                            : 1} color="bg-emerald-500" />
                        </div>
                        <div className="grid grid-cols-2 gap-3 pt-2">
                          <div className="bg-gray-50 rounded-lg p-3">
                            <p className="text-xs text-gray-400">RAG queries</p>
                            <p className="text-lg font-semibold text-gray-900">{monitoring.rag_requests}</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <p className="text-xs text-gray-400">Agent runs</p>
                            <p className="text-lg font-semibold text-gray-900">{monitoring.agent_requests}</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <p className="text-xs text-gray-400">Errors</p>
                            <p className={`text-lg font-semibold ${monitoring.error_count > 0 ? "text-red-600" : "text-gray-900"}`}>
                              {monitoring.error_count}
                            </p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <p className="text-xs text-gray-400">Est. cost</p>
                            <p className="text-lg font-semibold text-gray-900">${monitoring.estimated_cost_usd.toFixed(4)}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* MLflow deep link */}
                  <div className="card border-violet-100 bg-violet-50/30">
                    <div className="flex items-center gap-3">
                      <FlaskConical className="w-5 h-5 text-violet-600 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800">MLflow experiment tracking</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Every RAG query and agent run is logged as an MLflow run — view experiments,
                          compare parameters, and analyse metrics in the full MLflow UI.
                        </p>
                      </div>
                      <a href={mlflowUrl} target="_blank" rel="noopener noreferrer"
                        className="btn-primary text-sm flex items-center gap-1.5 flex-shrink-0">
                        <ExternalLink className="w-3.5 h-3.5" /> Open MLflow
                      </a>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
