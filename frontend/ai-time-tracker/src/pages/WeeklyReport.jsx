// src/pages/WeeklyReport.jsx
import React, { useEffect, useState } from "react";
import { Clock, Zap, Users, BarChart3 } from "lucide-react";
import { BASE_URL } from "../config";
import { useParams } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

export default function WeeklyReport() {
  const { id } = useParams();
  const userId = id;
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId) return;

    const token = localStorage.getItem("token");
    setLoading(true);

    fetch(`${BASE_URL}/api/admin/users/${userId}/weekly-report`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching weekly report:", err);
        setError("Failed to load weekly report");
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <p className="p-6">Loading weekly report...</p>;
  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!report) return <p className="p-6">No data available</p>;

  const { week_start, week_end, summary, category_breakdown, daily_breakdown, screenshots = [] } =
    report;

  const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#A569BD", "#5DADE2"];

  // Convert backend breakdowns to chart data
  const categoryData = Object.entries(category_breakdown || {}).map(([name, value]) => ({
    name,
    value,
  }));

  const dailyData = Object.entries(daily_breakdown || {}).map(([day, value]) => ({
    day,
    hours: value / 60,
  }));

  const clientData = (summary?.top_clients || []).map(([client, count]) => ({
    client,
    sessions: count,
  }));

  // Fake productivity trend using daily avg (backend can be extended to provide actual trend)
  const productivityTrend = dailyData.map((d, i) => ({
    day: d.day,
    avgScore: (Math.random() * (10 - 5) + 5).toFixed(1), // placeholder between 5–10
  }));

  return (
    <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">
        Weekly Report for <span className="text-blue-600">{report.username}</span> <br />
        <span className="text-gray-600 text-lg">
            ({week_start} → {week_end})
        </span>
        </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-600">Total Hours</p>
            <p className="text-2xl font-bold text-gray-900">{summary.total_hours}h</p>
          </div>
          <Clock className="text-blue-500 w-8 h-8" />
        </div>
        <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-600">Productive Hours</p>
            <p className="text-2xl font-bold text-green-600">{summary.productive_hours}h</p>
          </div>
          <Zap className="text-green-500 w-8 h-8" />
        </div>
        <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-600">Top Clients</p>
            <p className="text-md font-bold text-purple-600">
              {summary.top_clients && summary.top_clients.length > 0
                ? summary.top_clients.map((c) => c[0]).join(", ")
                : "None"}
            </p>
          </div>
          <Users className="text-purple-500 w-8 h-8" />
        </div>
        <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-600">Avg Productivity</p>
            <p className="text-2xl font-bold text-orange-600">{summary.avg_productivity}/10</p>
          </div>
          <BarChart3 className="text-orange-500 w-8 h-8" />
        </div>
      </div>

      {/* Charts */}
      {/* Category Pie */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Time by Category</h2>
        {categoryData.length === 0 ? (
          <p className="text-gray-500">No category data</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData}
                dataKey="value"
                nameKey="name"
                outerRadius={120}
                label={({ name, value }) => `${name}: ${(value / 60).toFixed(1)}h`}
              >
                {categoryData.map((_, i) => (
                  <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(val, name) => [`${(val / 60).toFixed(1)} hours`, name]} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Daily Bar */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Daily Hours</h2>
        {dailyData.length === 0 ? (
          <p className="text-gray-500">No daily data</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip formatter={(val) => `${val.toFixed(1)}h`} />
              <Bar dataKey="hours" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Productivity Trend */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Productivity Trend</h2>
        {productivityTrend.length === 0 ? (
          <p className="text-gray-500">No productivity data</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={productivityTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis domain={[0, 10]} />
              <Tooltip formatter={(val) => `${val}/10`} />
              <Line type="monotone" dataKey="avgScore" stroke="#10b981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Clients Bar */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Top Clients (Sessions)</h2>
        {clientData.length === 0 ? (
          <p className="text-gray-500">No client data</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={clientData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="client" />
              <YAxis />
              <Tooltip formatter={(val) => `${val} sessions`} />
              <Bar dataKey="sessions" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Screenshots */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Screenshots</h2>
        {screenshots.length === 0 ? (
          <p className="text-gray-500">No screenshots available</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {screenshots.map((s) => (
              <div key={s.id} className="border rounded-lg overflow-hidden shadow-sm">
                <img
                  src={`${BASE_URL}/${s.path}`}
                  alt="Screenshot"
                  className="w-full h-40 object-cover cursor-pointer"
                  onClick={() => window.open(`${BASE_URL}/${s.path}`, "_blank")}
                />
                <p className="text-xs text-gray-500 p-2 text-center">
                  {new Date(s.taken_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
