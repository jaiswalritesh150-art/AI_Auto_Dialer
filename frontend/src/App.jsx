import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function StatCard({ title, value, subtitle }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    completed: "bg-emerald-50 text-emerald-700",
    failed: "bg-red-50 text-red-700",
    queued: "bg-amber-50 text-amber-700",
    calling: "bg-blue-50 text-blue-700",
    initiated: "bg-blue-50 text-blue-700",
    in_progress: "bg-blue-50 text-blue-700",
  };

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${
        styles[status] || "bg-slate-100 text-slate-600"
      }`}
    >
      {status?.replaceAll("_", " ") || "unknown"}
    </span>
  );
}

function App() {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    try {
      setError("");

      const [statsRes, leadsRes, callsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/dashboard/stats`),
        fetch(`${API_BASE}/api/v1/leads`),
        fetch(`${API_BASE}/api/v1/call-attempts`),
      ]);

      if (!statsRes.ok || !leadsRes.ok || !callsRes.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const statsData = await statsRes.json();
      const leadsData = await leadsRes.json();
      const callsData = await callsRes.json();

      setStats(statsData.stats);
      setLeads(leadsData.leads || []);
      setCalls(callsData.call_attempts || []);
    } catch (err) {
      setError(err.message || "Unable to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(loadDashboard, 15000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Sidebar */}
      <aside className="fixed hidden h-screen w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-slate-200 px-6 py-6">
            <h1 className="text-xl font-bold tracking-tight">
              AI Auto Dialer
            </h1>
            <p className="mt-1 text-xs text-slate-500">
              Intelligent calling platform
            </p>
          </div>

          <nav className="flex-1 space-y-1 p-4">
            <button className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-semibold text-white">
              Dashboard
            </button>

            <button className="w-full rounded-xl px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-slate-100">
              Leads
            </button>

            <button className="w-full rounded-xl px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-slate-100">
              Call History
            </button>

            <button className="w-full rounded-xl px-4 py-3 text-left text-sm font-medium text-slate-600 hover:bg-slate-100">
              Callbacks
            </button>
          </nav>

          <div className="border-t border-slate-200 p-4">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-semibold text-slate-500">
                SYSTEM STATUS
              </p>
              <div className="mt-2 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <span className="text-sm font-medium text-slate-700">
                  Backend Connected
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="lg:ml-64">
        <header className="border-b border-slate-200 bg-white">
          <div className="flex items-center justify-between px-6 py-5 lg:px-8">
            <div>
              <h2 className="text-2xl font-bold">Dashboard</h2>
              <p className="mt-1 text-sm text-slate-500">
                Monitor your AI calling operations
              </p>
            </div>

            <button
              onClick={loadDashboard}
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              Refresh
            </button>
          </div>
        </header>

        <div className="space-y-8 p-6 lg:p-8">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Stats */}
          <section>
            <div className="mb-4">
              <h3 className="text-lg font-bold">Overview</h3>
              <p className="text-sm text-slate-500">
                Current system performance
              </p>
            </div>

            {loading && !stats ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                Loading dashboard...
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                <StatCard
                  title="Total Leads"
                  value={stats?.total_leads ?? 0}
                  subtitle="Leads in CRM"
                />

                <StatCard
                  title="Total Calls"
                  value={stats?.total_calls ?? 0}
                  subtitle="Call attempts"
                />

                <StatCard
                  title="Completed"
                  value={stats?.completed_calls ?? 0}
                  subtitle="Successful calls"
                />

                <StatCard
                  title="Failed"
                  value={stats?.failed_calls ?? 0}
                  subtitle="Failed attempts"
                />

                <StatCard
                  title="Avg. Duration"
                  value={`${stats?.average_call_duration_seconds ?? 0}s`}
                  subtitle="Average talk time"
                />
              </div>
            )}
          </section>

          {/* Recent Leads */}
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h3 className="font-bold">Recent Leads</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Latest leads received from CRM
                </p>
              </div>

              <span className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                {leads.length} total
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3">Lead</th>
                    <th className="px-6 py-3">Company</th>
                    <th className="px-6 py-3">Phone</th>
                    <th className="px-6 py-3">Score</th>
                    <th className="px-6 py-3">Priority</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {leads.slice(0, 8).map((lead) => (
                    <tr key={lead.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <p className="font-semibold">
                          {lead.first_name} {lead.last_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          {lead.email}
                        </p>
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {lead.company || "-"}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {lead.phone}
                      </td>

                      <td className="px-6 py-4">
                        <span className="font-semibold text-slate-800">
                          {lead.lead_score}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
                          {lead.priority}
                        </span>
                      </td>
                    </tr>
                  ))}

                  {!loading && leads.length === 0 && (
                    <tr>
                      <td
                        colSpan="5"
                        className="px-6 py-8 text-center text-sm text-slate-500"
                      >
                        No leads found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Recent Calls */}
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-5">
              <h3 className="font-bold">Recent Call Attempts</h3>
              <p className="mt-1 text-sm text-slate-500">
                Latest activity from the dialer
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3">Attempt</th>
                    <th className="px-6 py-3">Queue</th>
                    <th className="px-6 py-3">Provider</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Result</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {calls.slice(0, 8).map((call) => (
                    <tr key={call.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 font-semibold">
                        #{call.id}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        #{call.queue_id}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {call.provider || "—"}
                      </td>

                      <td className="px-6 py-4">
                        <StatusBadge status={call.status} />
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {call.result || call.failure_reason || "—"}
                      </td>
                    </tr>
                  ))}

                  {!loading && calls.length === 0 && (
                    <tr>
                      <td
                        colSpan="5"
                        className="px-6 py-8 text-center text-sm text-slate-500"
                      >
                        No call attempts found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;