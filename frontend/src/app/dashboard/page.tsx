"use client";
import { useState, useEffect } from "react";
import { FileText, MessageSquare, Zap, Database, Loader2 } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { dashboardApi } from "@/lib/api";

interface Stats {
  documents: {
    total: number;
    ready: number;
    processing: number;
    total_chunks: number;
    total_size_mb: number;
  };
  queries: {
    total_conversations: number;
    total_messages: number;
  };
  tokens: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  providers: Record<string, number>;
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = "text-primary-600",
  bg = "bg-primary-50",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  bg?: string;
}) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div>
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-semibold text-gray-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .getStats()
      .then(({ data }) => setStats(data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-6 max-w-4xl">
          <h1 className="text-xl font-semibold text-gray-900 mb-1">Dashboard</h1>
          <p className="text-sm text-gray-400 mb-6">Platform usage and analytics</p>

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* Stat cards */}
              <div className="grid grid-cols-2 gap-4">
                <StatCard
                  icon={FileText}
                  label="Documents"
                  value={stats.documents.total}
                  sub={`${stats.documents.ready} ready · ${stats.documents.processing} processing`}
                  color="text-blue-600"
                  bg="bg-blue-50"
                />
                <StatCard
                  icon={Database}
                  label="Indexed chunks"
                  value={stats.documents.total_chunks.toLocaleString()}
                  sub={`${stats.documents.total_size_mb} MB total`}
                  color="text-violet-600"
                  bg="bg-violet-50"
                />
                <StatCard
                  icon={MessageSquare}
                  label="Conversations"
                  value={stats.queries.total_conversations}
                  sub={`${stats.queries.total_messages} total messages`}
                  color="text-emerald-600"
                  bg="bg-emerald-50"
                />
                <StatCard
                  icon={Zap}
                  label="Tokens used"
                  value={stats.tokens.total_tokens.toLocaleString()}
                  sub={`${stats.tokens.prompt_tokens.toLocaleString()} prompt · ${stats.tokens.completion_tokens.toLocaleString()} completion`}
                  color="text-amber-600"
                  bg="bg-amber-50"
                />
              </div>

              {/* Provider usage */}
              {Object.keys(stats.providers).length > 0 && (
                <div className="card">
                  <p className="text-sm font-medium text-gray-700 mb-4">LLM provider usage</p>
                  <div className="space-y-3">
                    {Object.entries(stats.providers).map(([provider, count]) => {
                      const total = Object.values(stats.providers).reduce((a, b) => a + b, 0);
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={provider}>
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span className="capitalize font-medium">{provider}</span>
                            <span>{count} queries · {pct}%</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary-500 rounded-full"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* MLOps teaser */}
              <div className="card border-dashed border-2 border-gray-200 bg-gray-50/50">
                <p className="text-sm font-medium text-gray-500 mb-1">
                  🔬 MLOps layer coming in V3
                </p>
                <p className="text-xs text-gray-400">
                  MLflow experiment tracking, per-model accuracy benchmarks, cost analysis,
                  and automatic model selection — all built on top of the usage data captured here.
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Could not load stats.</p>
          )}
        </div>
      </main>
    </div>
  );
}
