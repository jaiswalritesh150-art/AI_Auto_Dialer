import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/* =========================
   Helpers
========================= */

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString();
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || seconds === "") {
    return "—";
  }

  const value = Number(seconds);

  if (!Number.isFinite(value)) {
    return "—";
  }

  if (value < 60) {
    return `${Math.round(value)}s`;
  }

  const minutes = Math.floor(value / 60);
  const remainingSeconds = Math.round(value % 60);

  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

/* =========================
   Reusable UI
========================= */

function StatCard({ title, value, subtitle }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">
        {title}
      </p>

      <p className="mt-2 text-3xl font-bold text-slate-900">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-400">
        {subtitle}
      </p>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalizedStatus = String(status || "").toLowerCase();

  const styles = {
    completed: "bg-emerald-50 text-emerald-700",
    failed: "bg-red-50 text-red-700",
    queued: "bg-amber-50 text-amber-700",
    calling: "bg-blue-50 text-blue-700",
    initiated: "bg-blue-50 text-blue-700",
    in_progress: "bg-blue-50 text-blue-700",
    scheduled: "bg-purple-50 text-purple-700",
    pending: "bg-amber-50 text-amber-700",
    processed: "bg-emerald-50 text-emerald-700",
    ready: "bg-purple-50 text-purple-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        styles[normalizedStatus] || "bg-slate-100 text-slate-600"
      }`}
    >
      {normalizedStatus
        ? normalizedStatus.replaceAll("_", " ")
        : "unknown"}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const normalizedPriority = String(
    priority || ""
  ).toUpperCase();

  const styles = {
    HIGH: "bg-red-50 text-red-700",
    MEDIUM: "bg-amber-50 text-amber-700",
    LOW: "bg-emerald-50 text-emerald-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        styles[normalizedPriority] ||
        "bg-slate-100 text-slate-600"
      }`}
    >
      {priority || "—"}
    </span>
  );
}

/* =========================
   Dashboard
========================= */

function DashboardPage({
  stats,
  leads,
  calls,
  loading,
}) {
  const recentLeads = [...leads]
    .sort(
      (a, b) =>
        Number(b.id || 0) - Number(a.id || 0)
    )
    .slice(0, 8);

  const recentCalls = [...calls]
    .sort(
      (a, b) =>
        Number(b.id || 0) - Number(a.id || 0)
    )
    .slice(0, 8);

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4">
          <h3 className="text-lg font-bold">
            Overview
          </h3>

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
              value={formatDuration(
                stats?.average_call_duration_seconds
              )}
              subtitle="Average talk time"
            />
          </div>
        )}
      </section>

      {/* Recent Leads */}

      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h3 className="font-bold">
              Recent Leads
            </h3>

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
                <th className="px-6 py-3">
                  Lead
                </th>
                <th className="px-6 py-3">
                  Company
                </th>
                <th className="px-6 py-3">
                  Phone
                </th>
                <th className="px-6 py-3">
                  Score
                </th>
                <th className="px-6 py-3">
                  Priority
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {recentLeads.map((lead) => (
                <tr
                  key={lead.id}
                  className="transition hover:bg-slate-50"
                >
                  <td className="px-6 py-4">
                    <p className="font-semibold">
                      {lead.first_name}{" "}
                      {lead.last_name}
                    </p>

                    <p className="text-xs text-slate-500">
                      {lead.email || "—"}
                    </p>
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    {lead.company || "—"}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    {lead.phone || "—"}
                  </td>

                  <td className="px-6 py-4">
                    <span className="font-semibold text-slate-800">
                      {lead.lead_score ?? "—"}
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    <PriorityBadge
                      priority={lead.priority}
                    />
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
          <h3 className="font-bold">
            Recent Call Attempts
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Latest activity from the dialer
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3">
                  Attempt
                </th>
                <th className="px-6 py-3">
                  Queue
                </th>
                <th className="px-6 py-3">
                  Provider
                </th>
                <th className="px-6 py-3">
                  Status
                </th>
                <th className="px-6 py-3">
                  Result
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {recentCalls.map((call) => (
                <tr
                  key={call.id}
                  className="transition hover:bg-slate-50"
                >
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
                    <StatusBadge
                      status={call.status}
                    />
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    {call.result ||
                      call.failure_reason ||
                      "—"}
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
  );
}

/* =========================
   Leads
========================= */

function LeadsPage({ leads, loading }) {
  const sortedLeads = [...leads].sort(
    (a, b) =>
      Number(b.id || 0) - Number(a.id || 0)
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
        <div>
          <h3 className="text-lg font-bold">
            All Leads
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Leads received from Zoho CRM
          </p>
        </div>

        <span className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
          {leads.length} leads
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-6 py-3">ID</th>
              <th className="px-6 py-3">Lead</th>
              <th className="px-6 py-3">Company</th>
              <th className="px-6 py-3">Phone</th>
              <th className="px-6 py-3">Source</th>
              <th className="px-6 py-3">Score</th>
              <th className="px-6 py-3">Priority</th>
              <th className="px-6 py-3">Status</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {sortedLeads.map((lead) => (
              <tr
                key={lead.id}
                className="transition hover:bg-slate-50"
              >
                <td className="px-6 py-4 text-sm font-semibold">
                  #{lead.id}
                </td>

                <td className="px-6 py-4">
                  <p className="font-semibold">
                    {lead.first_name}{" "}
                    {lead.last_name}
                  </p>

                  <p className="text-xs text-slate-500">
                    {lead.email || "—"}
                  </p>
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  {lead.company || "—"}
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  {lead.phone || "—"}
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  {lead.lead_source || "—"}
                </td>

                <td className="px-6 py-4 font-semibold">
                  {lead.lead_score ?? "—"}
                </td>

                <td className="px-6 py-4">
                  <PriorityBadge
                    priority={lead.priority}
                  />
                </td>

                <td className="px-6 py-4">
                  <StatusBadge
                    status={lead.lead_status}
                  />
                </td>
              </tr>
            ))}

            {!loading && leads.length === 0 && (
              <tr>
                <td
                  colSpan="8"
                  className="px-6 py-10 text-center text-sm text-slate-500"
                >
                  No leads found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* =========================
   Call Queue
========================= */

function CallQueuePage({
  queue,
  loading,
  onProcessQueueCall,
  processingQueueId,
}) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] =
    useState("all");
  const [priorityFilter, setPriorityFilter] =
    useState("all");

  const sortedQueue = [...queue].sort(
    (a, b) =>
      Number(b.id || 0) - Number(a.id || 0)
  );

  const filteredQueue = sortedQueue.filter(
    (item) => {
      const searchText = search
        .trim()
        .toLowerCase();

      const matchesSearch =
        !searchText ||
        String(item.id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(item.lead_id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(item.phone || "")
          .toLowerCase()
          .includes(searchText) ||
        String(item.status || "")
          .toLowerCase()
          .includes(searchText) ||
        String(item.failure_reason || "")
          .toLowerCase()
          .includes(searchText);

      const matchesStatus =
        statusFilter === "all" ||
        String(item.status || "").toLowerCase() ===
          statusFilter;

      const itemPriority = String(
        item.priority || ""
      ).toLowerCase();

      const matchesPriority =
        priorityFilter === "all" ||
        itemPriority === priorityFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesPriority
      );
    }
  );

  const total = queue.length;

  const queued = queue.filter(
    (item) => item.status === "queued"
  ).length;

  const calling = queue.filter(
    (item) =>
      item.status === "calling" ||
      item.status === "initiated" ||
      item.status === "in_progress"
  ).length;

  const completed = queue.filter(
    (item) => item.status === "completed"
  ).length;

  const failed = queue.filter(
    (item) => item.status === "failed"
  ).length;

  const callbacks = queue.filter(
    (item) =>
      item.callback_at ||
      item.callback_status
  ).length;

  const canProcess = (item) =>
    item.status === "queued" ||
    item.status === "failed";

  return (
    <div className="space-y-6">
      {/* Queue Summary */}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <StatCard
          title="Total Queue"
          value={total}
          subtitle="All queue items"
        />

        <StatCard
          title="Queued"
          value={queued}
          subtitle="Waiting to process"
        />

        <StatCard
          title="Calling"
          value={calling}
          subtitle="Currently active"
        />

        <StatCard
          title="Completed"
          value={completed}
          subtitle="Processed successfully"
        />

        <StatCard
          title="Failed"
          value={failed}
          subtitle="Failed queue items"
        />

        <StatCard
          title="Callbacks"
          value={callbacks}
          subtitle="Scheduled follow-ups"
        />
      </div>

      {/* Queue Table */}

      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-lg font-bold">
                Call Queue
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Leads waiting for or processed by
                the dialer
              </p>
            </div>

            <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
              {filteredQueue.length} of {total} queue
              items
            </div>
          </div>

          {/* Search + Filters */}

          <div className="mt-5 flex flex-col gap-3 lg:flex-row">
            <input
              type="text"
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              placeholder="Search by queue ID, lead ID, phone..."
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100 lg:flex-1"
            />

            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value)
              }
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
            >
              <option value="all">
                All Status
              </option>
              <option value="queued">
                Queued
              </option>
              <option value="calling">
                Calling
              </option>
              <option value="initiated">
                Initiated
              </option>
              <option value="in_progress">
                In Progress
              </option>
              <option value="completed">
                Completed
              </option>
              <option value="failed">
                Failed
              </option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) =>
                setPriorityFilter(e.target.value)
              }
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
            >
              <option value="all">
                All Priority
              </option>
              <option value="high">High</option>
              <option value="medium">
                Medium
              </option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {loading && queue.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-500">
            Loading call queue...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1450px] text-left">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-3">
                    Queue
                  </th>
                  <th className="px-6 py-3">
                    Lead
                  </th>
                  <th className="px-6 py-3">
                    Phone
                  </th>
                  <th className="px-6 py-3">
                    Priority
                  </th>
                  <th className="px-6 py-3">
                    Status
                  </th>
                  <th className="px-6 py-3">
                    Queued At
                  </th>
                  <th className="px-6 py-3">
                    Started At
                  </th>
                  <th className="px-6 py-3">
                    Callback
                  </th>
                  <th className="px-6 py-3">
                    Reason
                  </th>
                  <th className="px-6 py-3">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {filteredQueue.map((item) => {
                  const isProcessing =
                    processingQueueId === item.id;

                  return (
                    <tr
                      key={item.id}
                      className="transition hover:bg-slate-50"
                    >
                      <td className="px-6 py-4 font-semibold">
                        #{item.id}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        #{item.lead_id ?? "—"}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {item.phone || "—"}
                      </td>

                      <td className="px-6 py-4">
                        <PriorityBadge
                          priority={item.priority}
                        />
                      </td>

                      <td className="px-6 py-4">
                        <StatusBadge
                          status={item.status}
                        />
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {formatDate(
                          item.queued_at
                        )}
                      </td>

                      <td className="px-6 py-4 text-sm text-slate-600">
                        {formatDate(
                          item.started_at
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <p className="text-sm text-slate-600">
                            {formatDate(
                              item.callback_at
                            )}
                          </p>

                          {item.callback_status && (
                            <StatusBadge
                              status={
                                item.callback_status
                              }
                            />
                          )}
                        </div>
                      </td>

                      <td className="max-w-xs px-6 py-4">
                        {item.failure_reason ? (
                          <span className="text-sm font-medium text-red-600">
                            {item.failure_reason}
                          </span>
                        ) : (
                          <span className="text-sm text-slate-400">
                            —
                          </span>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        {canProcess(item) ? (
                          <button
                            onClick={() =>
                              onProcessQueueCall(
                                item.id
                              )
                            }
                            disabled={
                              isProcessing ||
                              processingQueueId !==
                                null
                            }
                            className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold text-white transition ${
                              isProcessing ||
                              processingQueueId !==
                                null
                                ? "cursor-not-allowed bg-slate-400"
                                : item.status ===
                                  "failed"
                                ? "bg-red-600 hover:bg-red-700"
                                : "bg-emerald-600 hover:bg-emerald-700"
                            }`}
                          >
                            {isProcessing
                              ? "Processing..."
                              : item.status ===
                                "failed"
                              ? "Retry Call"
                              : "Process Call"}
                          </button>
                        ) : (
                          <span className="text-xs font-medium text-slate-400">
                            —
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}

                {!loading &&
                  filteredQueue.length === 0 && (
                    <tr>
                      <td
                        colSpan="10"
                        className="px-6 py-12 text-center"
                      >
                        <div className="text-sm font-semibold text-slate-700">
                          No queue items found
                        </div>

                        <div className="mt-1 text-xs text-slate-500">
                          Try changing your search
                          or filters.
                        </div>
                      </td>
                    </tr>
                  )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

/* =========================
   Call History
========================= */

function CallHistoryPage({
  calls,
  loading,
}) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] =
    useState("all");

  const sortedCalls = [...calls].sort(
    (a, b) =>
      Number(b.id || 0) - Number(a.id || 0)
  );

  const filteredCalls = sortedCalls.filter(
    (call) => {
      const searchText = search
        .trim()
        .toLowerCase();

      const matchesSearch =
        !searchText ||
        String(call.id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(call.queue_id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(call.provider || "")
          .toLowerCase()
          .includes(searchText) ||
        String(call.result || "")
          .toLowerCase()
          .includes(searchText) ||
        String(call.failure_reason || "")
          .toLowerCase()
          .includes(searchText) ||
        String(call.provider_call_id || "")
          .toLowerCase()
          .includes(searchText);

      const matchesStatus =
        statusFilter === "all" ||
        String(call.status || "").toLowerCase() ===
          statusFilter;

      return (
        matchesSearch && matchesStatus
      );
    }
  );

  const statusOptions = [
    { value: "all", label: "All Status" },
    {
      value: "completed",
      label: "Completed",
    },
    {
      value: "failed",
      label: "Failed",
    },
    {
      value: "started",
      label: "Started",
    },
    {
      value: "initiated",
      label: "Initiated",
    },
  ];

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-bold">
              Call History
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              Review complete dialer call activity
            </p>
          </div>

          <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
            {filteredCalls.length} of{" "}
            {calls.length} attempts
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3 md:flex-row">
          <input
            type="text"
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            placeholder="Search by ID, queue, provider, result..."
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100 md:flex-1"
          />

          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
          >
            {statusOptions.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1250px] text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-6 py-3">
                Attempt
              </th>
              <th className="px-6 py-3">
                Queue
              </th>
              <th className="px-6 py-3">
                Attempt #
              </th>
              <th className="px-6 py-3">
                Provider
              </th>
              <th className="px-6 py-3">
                Status
              </th>
              <th className="px-6 py-3">
                Result
              </th>
              <th className="px-6 py-3">
                Duration
              </th>
              <th className="px-6 py-3">
                Failure Reason
              </th>
              <th className="px-6 py-3">
                Started
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td
                  colSpan="9"
                  className="px-6 py-10 text-center text-sm text-slate-500"
                >
                  Loading call history...
                </td>
              </tr>
            )}

            {!loading &&
              filteredCalls.map((call) => (
                <tr
                  key={call.id}
                  className="transition hover:bg-slate-50"
                >
                  <td className="px-6 py-4 font-semibold">
                    #{call.id}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    #{call.queue_id ?? "—"}
                  </td>

                  <td className="px-6 py-4 text-sm font-medium text-slate-700">
                    {call.attempt_number ?? "—"}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    {call.provider || "—"}
                  </td>

                  <td className="px-6 py-4">
                    <StatusBadge
                      status={call.status}
                    />
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-600">
                    {call.result || "—"}
                  </td>

                  <td className="px-6 py-4 text-sm font-medium text-slate-700">
                    {formatDuration(
                      call.duration_seconds
                    )}
                  </td>

                  <td className="max-w-xs px-6 py-4 text-sm text-slate-500">
                    {call.failure_reason || "—"}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-500">
                    {formatDate(
                      call.started_at
                    )}
                  </td>
                </tr>
              ))}

            {!loading &&
              filteredCalls.length === 0 && (
                <tr>
                  <td
                    colSpan="9"
                    className="px-6 py-12 text-center"
                  >
                    <div className="text-sm font-semibold text-slate-700">
                      No call history found
                    </div>

                    <div className="mt-1 text-xs text-slate-500">
                      Try changing your search or
                      status filter.
                    </div>
                  </td>
                </tr>
              )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* =========================
   Callbacks
========================= */

function CallbacksPage({
  queue,
  loading,
}) {
  const callbacks = [...queue]
    .filter(
      (item) =>
        item.callback_at ||
        item.callback_status
    )
    .sort(
      (a, b) =>
        new Date(
          a.callback_at || 0
        ).getTime() -
        new Date(
          b.callback_at || 0
        ).getTime()
    );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
        <div>
          <h3 className="text-lg font-bold">
            Callbacks
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Scheduled callbacks and follow-up activity
          </p>
        </div>

        <span className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
          {callbacks.length} scheduled
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-6 py-3">
                Queue
              </th>
              <th className="px-6 py-3">
                Lead ID
              </th>
              <th className="px-6 py-3">
                Phone
              </th>
              <th className="px-6 py-3">
                Callback Time
              </th>
              <th className="px-6 py-3">
                Callback Status
              </th>
              <th className="px-6 py-3">
                Queue Status
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {callbacks.map((item) => (
              <tr
                key={item.id}
                className="transition hover:bg-slate-50"
              >
                <td className="px-6 py-4 font-semibold">
                  #{item.id}
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  #{item.lead_id}
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  {item.phone || "—"}
                </td>

                <td className="px-6 py-4 text-sm text-slate-600">
                  {formatDate(
                    item.callback_at
                  )}
                </td>

                <td className="px-6 py-4">
                  <StatusBadge
                    status={
                      item.callback_status
                    }
                  />
                </td>

                <td className="px-6 py-4">
                  <StatusBadge
                    status={item.status}
                  />
                </td>
              </tr>
            ))}

            {!loading &&
              callbacks.length === 0 && (
                <tr>
                  <td
                    colSpan="6"
                    className="px-6 py-10 text-center text-sm text-slate-500"
                  >
                    No callbacks scheduled
                  </td>
                </tr>
              )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* =========================
   Main App
========================= */

function App() {
  const [activePage, setActivePage] =
    useState("dashboard");

  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [calls, setCalls] = useState([]);
  const [queue, setQueue] = useState([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [processingCall, setProcessingCall] =
    useState(false);

  const [processingQueueId, setProcessingQueueId] =
    useState(null);

  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] =
    useState(null);

  /* =========================
     Load Dashboard
  ========================= */

  const loadDashboard = async (
    isManualRefresh = false
  ) => {
    try {
      if (isManualRefresh) {
        setRefreshing(true);
      }

      setError("");

      const [
        statsRes,
        leadsRes,
        callsRes,
        queueRes,
      ] = await Promise.all([
        fetch(
          `${API_BASE}/api/v1/dashboard/stats`
        ),
        fetch(
          `${API_BASE}/api/v1/leads`
        ),
        fetch(
          `${API_BASE}/api/v1/call-attempts`
        ),
        fetch(
          `${API_BASE}/api/v1/call-queue`
        ),
      ]);

      if (
        !statsRes.ok ||
        !leadsRes.ok ||
        !callsRes.ok ||
        !queueRes.ok
      ) {
        throw new Error(
          "Failed to load dashboard data"
        );
      }

      const statsData =
        await statsRes.json();

      const leadsData =
        await leadsRes.json();

      const callsData =
        await callsRes.json();

      const queueData =
        await queueRes.json();

      setStats(
        statsData.stats || null
      );

      setLeads(
        leadsData.leads || []
      );

      setCalls(
        callsData.call_attempts || []
      );

      setQueue(
        queueData.call_queue ||
          queueData.queue ||
          []
      );

      setLastUpdated(new Date());
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to backend"
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /* =========================
     Process Next Queue Call
  ========================= */

  const processNextCall = async () => {
    try {
      setProcessingCall(true);
      setError("");

      const response = await fetch(
        `${API_BASE}/api/v1/dialer/process-next`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (
        !response.ok ||
        data.success === false
      ) {
        throw new Error(
          data.message ||
            "Failed to process next call"
        );
      }

      await loadDashboard(true);
    } catch (err) {
      setError(
        err.message ||
          "Unable to process next call"
      );
    } finally {
      setProcessingCall(false);
    }
  };

  /* =========================
     Process Specific Queue
  ========================= */

  const processQueueCall = async (
    queueId
  ) => {
    try {
      setProcessingQueueId(queueId);
      setError("");

      const response = await fetch(
        `${API_BASE}/api/v1/dialer/process/${queueId}`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (
        !response.ok ||
        data.success === false
      ) {
        throw new Error(
          data.message ||
            `Failed to process queue #${queueId}`
        );
      }

      await loadDashboard(true);
    } catch (err) {
      setError(
        err.message ||
          "Unable to process queue call"
      );
    } finally {
      setProcessingQueueId(null);
    }
  };

  /* =========================
     Auto Refresh
  ========================= */

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(() => {
      loadDashboard();
    }, 15000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  /* =========================
     Navigation
  ========================= */

  const navigation = [
    {
      id: "dashboard",
      label: "Dashboard",
    },
    {
      id: "leads",
      label: "Leads",
    },
    {
      id: "queue",
      label: "Call Queue",
    },
    {
      id: "calls",
      label: "Call History",
    },
    {
      id: "callbacks",
      label: "Callbacks",
    },
  ];

  const pageTitles = {
    dashboard: {
      title: "Dashboard",
      subtitle:
        "Monitor your AI calling operations",
    },

    leads: {
      title: "Leads",
      subtitle:
        "Manage leads received from Zoho CRM",
    },

    queue: {
      title: "Call Queue",
      subtitle:
        "Monitor leads processed by the dialer",
    },

    calls: {
      title: "Call History",
      subtitle:
        "Review dialer call activity",
    },

    callbacks: {
      title: "Callbacks",
      subtitle:
        "Manage scheduled follow-ups",
    },
  };

  /* =========================
     Render Active Page
  ========================= */

  const renderPage = () => {
    if (activePage === "leads") {
      return (
        <LeadsPage
          leads={leads}
          loading={loading}
        />
      );
    }

    if (activePage === "queue") {
      return (
        <CallQueuePage
          queue={queue}
          loading={loading}
          onProcessQueueCall={
            processQueueCall
          }
          processingQueueId={
            processingQueueId
          }
        />
      );
    }

    if (activePage === "calls") {
      return (
        <CallHistoryPage
          calls={calls}
          loading={loading}
        />
      );
    }

    if (activePage === "callbacks") {
      return (
        <CallbacksPage
          queue={queue}
          loading={loading}
        />
      );
    }

    return (
      <DashboardPage
        stats={stats}
        leads={leads}
        calls={calls}
        loading={loading}
      />
    );
  };

  const backendConnected =
    !error && !loading;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* =========================
          Desktop Sidebar
      ========================= */}

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
            {navigation.map((item) => (
              <button
                key={item.id}
                onClick={() =>
                  setActivePage(item.id)
                }
                className={`w-full rounded-xl px-4 py-3 text-left text-sm font-semibold transition ${
                  activePage === item.id
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="border-t border-slate-200 p-4">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-semibold text-slate-500">
                SYSTEM STATUS
              </p>

              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    loading
                      ? "bg-amber-500"
                      : backendConnected
                      ? "bg-emerald-500"
                      : "bg-red-500"
                  }`}
                />

                <span className="text-sm font-medium text-slate-700">
                  {loading
                    ? "Connecting..."
                    : backendConnected
                    ? "Backend Connected"
                    : "Backend Error"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* =========================
          Main
      ========================= */}

      <main className="lg:ml-64">
        {/* Header */}

        <header className="border-b border-slate-200 bg-white">
          <div className="px-6 py-5 lg:px-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-bold">
                  {pageTitles[activePage].title}
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {
                    pageTitles[activePage]
                      .subtitle
                  }
                </p>
              </div>

              <div className="flex items-center gap-3">
                {lastUpdated && (
                  <span className="hidden text-xs text-slate-400 md:block">
                    Updated{" "}
                    {lastUpdated.toLocaleTimeString()}
                  </span>
                )}

                <button
                  onClick={processNextCall}
                  disabled={
                    processingCall ||
                    processingQueueId !==
                      null ||
                    refreshing ||
                    loading
                  }
                  className={`rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition ${
                    processingCall ||
                    processingQueueId !==
                      null ||
                    refreshing ||
                    loading
                      ? "cursor-not-allowed bg-slate-400"
                      : "bg-emerald-600 hover:bg-emerald-700"
                  }`}
                >
                  {processingCall
                    ? "Processing..."
                    : "Process Next Call"}
                </button>

                <button
                  onClick={() =>
                    loadDashboard(true)
                  }
                  disabled={
                    refreshing ||
                    processingCall ||
                    processingQueueId !==
                      null
                  }
                  className={`rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition ${
                    refreshing ||
                    processingCall ||
                    processingQueueId !==
                      null
                      ? "cursor-not-allowed bg-slate-400"
                      : "bg-slate-900 hover:bg-slate-800"
                  }`}
                >
                  {refreshing
                    ? "Refreshing..."
                    : "Refresh"}
                </button>
              </div>
            </div>

            {/* Mobile Navigation */}

            <div className="mt-4 flex gap-2 overflow-x-auto lg:hidden">
              {navigation.map((item) => (
                <button
                  key={item.id}
                  onClick={() =>
                    setActivePage(item.id)
                  }
                  className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold transition ${
                    activePage === item.id
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Content */}

        <div className="space-y-8 p-6 lg:p-8">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-semibold">
                Backend connection error
              </div>

              <div className="mt-1">
                {error}
              </div>
            </div>
          )}

          {renderPage()}
        </div>
      </main>
    </div>
  );
}

export default App;