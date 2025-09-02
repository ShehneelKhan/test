// src/pages/AdminDashboard.jsx
import React, { useEffect, useState } from "react";
import { Clock, Activity, Users, BarChart3, Eye, Zap } from "lucide-react";
import { BASE_URL } from "../config"; // ✅ import the BASE_URL
import { useNavigate } from "react-router-dom";

export default function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [showClientForm, setShowClientForm] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const navigate = useNavigate();
  const [selectedUser, setSelectedUser] = useState(null);
  const [currentScreenshot, setCurrentScreenshot] = useState(null);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [activities, setActivities] = useState([]);
  const [screenshots, setScreenshots] = useState([]);
  const [summary, setSummary] = useState({
    totalTime: 0,
    productiveTime: 0,
    clientsWorkedWith: 0,
    averageProductivity: 0,
  });
  const [currentActivity, setCurrentActivity] = useState(null);

  // ✅ Fetch all users on mount
  useEffect(() => {
    fetch(`${BASE_URL}/api/admin/users`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => setUsers(data || []))
      .catch((err) => console.error("Error fetching users:", err));
  }, []);

  // ✅ Fetch activities & screenshots when user or date changes
  useEffect(() => {
    if (!selectedUser) return;

    const token = localStorage.getItem("token");

    // Fetch activities
    fetch(
      `${BASE_URL}/api/admin/users/${selectedUser.id}/activities-by-date?date=${selectedDate}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    )
      .then((res) => res.json())
      .then((data) => {
        setActivities(data || []);
        calculateSummary(data);
      })
      .catch((err) => console.error("Error fetching activities:", err));

    // Fetch screenshots
    fetch(
      `${BASE_URL}/api/admin/users/${selectedUser.id}/screenshots-by-date?date=${selectedDate}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    )
      .then((res) => res.json())
      .then((data) => setScreenshots(data || []))
      .catch((err) => console.error("Error fetching screenshots:", err));
  }, [selectedUser, selectedDate]);


  // ✅ Calculate summary like App.js
  const calculateSummary = (activities) => {
    const totalTime = activities.reduce(
      (sum, activity) => sum + (activity.duration_minutes || 0),
      0
    );
    const productiveTime = activities
      .filter((activity) => activity.productivity_score >= 7)
      .reduce((sum, activity) => sum + (activity.duration_minutes || 0), 0);

    const uniqueClients = new Set(
      activities
        .map((activity) => activity.client_identified)
        .filter((client) => client && client !== "None")
    );

    const avgProductivity =
      activities.length > 0
        ? activities.reduce(
            (sum, activity) => sum + activity.productivity_score,
            0
          ) / activities.length
        : 0;

    setSummary({
      totalTime: Math.round((totalTime / 60) * 100) / 100,
      productiveTime: Math.round((productiveTime / 60) * 100) / 100,
      clientsWorkedWith: uniqueClients.size,
      averageProductivity:
        totalTime > 0
          ? Math.round((productiveTime / totalTime) * 10 * 10) / 10
          : 0,
    });
  };

  // ✅ Helpers copied from App.js
  const formatDuration = (minutes) => {
    if (!minutes) return "0m";
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0 && mins < 1) {
      return `${minutes.toFixed(2)}m`;
    }
    return hours > 0 ? `${hours}h ${Math.round(mins)}m` : `${Math.round(mins)}m`;
  };

  const getProductivityColor = (score) => {
    if (score >= 8) return "bg-green-100 text-green-800 border-green-300";
    if (score >= 6) return "bg-yellow-100 text-yellow-800 border-yellow-300";
    if (score >= 4) return "bg-orange-100 text-orange-800 border-orange-300";
    return "bg-red-100 text-red-800 border-red-300";
  };

  const getStatusColor = (status) => {
    switch ((status || "").toLowerCase()) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-300";
      case "billed":
        return "bg-purple-100 text-purple-800 border-purple-300";
      case "in progress":
        return "bg-gray-100 text-gray-800 border-gray-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getEntryTypeColor = (entryType) => {
    switch (entryType || "") {
      case "Manual Entry":
        return "bg-purple-100 text-purple-800 border-purple-300";
      case "Automated Entry":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getCategoryIcon = (category) => {
    switch (category?.toLowerCase()) {
      case "work":
        return <BarChart3 className="w-4 h-4" />;
      case "communication":
        return <Users className="w-4 h-4" />;
      case "social":
        return <Users className="w-4 h-4" />;
      case "research":
        return <Eye className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  return (
  <div className="flex h-screen">
    {/* Sidebar */}
    <div className="w-1/4 border-r p-4 bg-gray-100">
        <button
          onClick={() => navigate("/admin/add-client")}
          className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm mb-4"
        >
          + Add Client
        </button>
        <h2 className="text-lg font-bold mb-4 flex justify-between items-center">
      Users
    </h2>
      {users.length === 0 ? (
        <p>No users found.</p>
      ) : (
        <ul className="space-y-2">
          {users.map((u) => (
            <li
              key={u.id}
              onClick={() => setSelectedUser(u)}
              className={`cursor-pointer p-2 rounded ${
                selectedUser?.id === u.id
                  ? "bg-blue-500 text-white"
                  : "hover:bg-gray-200"
              }`}
            >
              {u.name || u.email}
            </li>
          ))}
        </ul>
      )}
    </div>

    {/* Main content */}
    <div className="flex-1 p-6 overflow-y-auto">
      {!selectedUser ? (
        <p className="text-gray-600 text-lg">
          Select a user and date to view reports
        </p>
      ) : (
        <>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">
              Reports for {selectedUser.name || selectedUser.email}
            </h2>
            <div className="flex gap-3 items-center">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              {/* ✅ Weekly Report Button */}
              <button
                onClick={() => navigate(`/admin/weekly-report/${selectedUser.id}`)}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm"
              >
                Weekly Report
              </button>
            </div>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Total Time</p>
                <p className="text-2xl font-bold text-gray-900">
                  {summary.totalTime}h
                </p>
              </div>
              <Clock className="text-blue-500 w-8 h-8" />
            </div>
            <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Productive Time</p>
                <p className="text-2xl font-bold text-green-600">
                  {summary.productiveTime}h
                </p>
              </div>
              <Zap className="text-green-500 w-8 h-8" />
            </div>
            <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Clients</p>
                <p className="text-2xl font-bold text-purple-600">
                  {summary.clientsWorkedWith}
                </p>
              </div>
              <Users className="text-purple-500 w-8 h-8" />
            </div>
            <div className="bg-white rounded-lg shadow p-6 flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Avg Productivity</p>
                <p
                  className={`text-2xl font-bold ${
                    summary.averageProductivity <= 5
                      ? "text-red-600"
                      : summary.averageProductivity < 8
                      ? "text-yellow-600"
                      : "text-green-600"
                  }`}
                >
                  {summary.averageProductivity}/10
                </p>
              </div>
              <BarChart3 className="text-orange-500 w-8 h-8" />
            </div>
          </div>

          {/* Activities List */}
          <div className="bg-white rounded-lg shadow-lg mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                Activities for {selectedDate}
              </h2>
            </div>

            <div className="divide-y divide-gray-200">
              {activities.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No activities recorded for this date</p>
                </div>
              ) : (
                activities.map((activity) => {
                  let aiAnalysis = activity.ai_analysis || {};
                  return (
                    <div
                      key={activity.id}
                      onClick={() =>
                        setCurrentActivity({ ...activity, aiAnalysis })
                      }
                      className="p-6 hover:bg-gray-50 cursor-pointer"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4">
                          <div className="flex-shrink-0">
                            {getCategoryIcon(activity.category)}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="font-semibold text-gray-900">
                                {activity.application}
                              </h3>
                              <span
                                className={`px-2 py-1 text-xs border rounded-full ${getProductivityColor(
                                  activity.productivity_score
                                )}`}
                              >
                                Productivity: {activity.productivity_score}/10
                              </span>
                              {activity.entry_type && (
                                <span
                                  className={`px-2 py-1 text-xs border rounded-full ${getEntryTypeColor(
                                    activity.entry_type
                                  )}`}
                                >
                                  {activity.entry_type}
                                </span>
                              )}
                              {activity.entry_type !== "Automated Entry" &&
                                activity.status && (
                                  <span
                                    className={`px-2 py-1 text-xs border rounded-full ${getStatusColor(
                                      activity.status
                                    )}`}
                                  >
                                    {activity.status}
                                  </span>
                                )}
                              {activity.client_identified &&
                                activity.client_identified !== "None" && (
                                  <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 border border-blue-300 rounded-full">
                                    Client: {activity.client_identified}
                                  </span>
                                )}
                            </div>
                            <p className="text-gray-600 text-sm mb-2">
                              {activity.window_title}
                            </p>
                            {aiAnalysis.description && (
                              <p className="text-gray-700 text-sm">
                                {aiAnalysis.description}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-gray-500">
                            {new Date(activity.start_time).toLocaleTimeString()}{" "}
                            -{" "}
                            {activity.end_time
                              ? new Date(
                                  activity.end_time
                                ).toLocaleTimeString()
                              : "Ongoing"}
                          </p>
                          <p className="font-medium text-gray-900">
                            {formatDuration(activity.duration_minutes || 0)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Screenshots */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Screenshots for {selectedDate}
            </h2>
            {screenshots.length === 0 ? (
              <p className="text-gray-500">No screenshots available</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {screenshots.map((s) => (
                  <div
                    key={s.id}
                    className="border rounded-lg overflow-hidden shadow-sm"
                  >
                  <img
                    src={`${BASE_URL}/${s.path}`}
                    alt="Screenshot"
                    className="w-full h-40 object-cover cursor-pointer"
                    onClick={() => setCurrentScreenshot(s)}
                  />

                    <p className="text-xs text-gray-500 p-2 text-center">
                      {new Date(s.taken_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Screenshot Modal */}
          {currentScreenshot && (
          <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-70 z-50">
            <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full relative">
              <button
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
                onClick={() => setCurrentScreenshot(null)}
              >
                ✖
              </button>
              <img
                src={`${BASE_URL}/${currentScreenshot.path}`}
                alt="Screenshot"
                className="w-full h-auto rounded-lg"
              />
              <p className="text-xs text-gray-500 text-center p-2">
                {new Date(currentScreenshot.taken_at).toLocaleString()}
              </p>
            </div>
          </div>
        )}

          {/* Activity Detail Modal */}
          {currentActivity && (
            <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
              <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl p-6 relative">
                <button
                  className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
                  onClick={() => setCurrentActivity(null)}
                >
                  ✖
                </button>

                <h3 className="text-xl font-bold text-gray-900 mb-4">
                  {currentActivity.application} – Details
                </h3>

                <div className="space-y-3 text-sm text-gray-700 max-h-[70vh] overflow-y-auto pr-2">
                  <p>
                    <span className="font-semibold">Application:</span>{" "}
                    {currentActivity.application || ""}
                  </p>
                  <p>
                    <span className="font-semibold">Window Title:</span>{" "}
                    {currentActivity.window_title || ""}
                  </p>
                  {currentActivity.entry_type !== "Automated Entry" && (
                    <p>
                      <span className="font-semibold">Status:</span>{" "}
                      {currentActivity.status || "Unknown"}
                    </p>
                  )}
                  <p>
                    <span className="font-semibold">Duration:</span>{" "}
                    {formatDuration(currentActivity.duration_minutes || 0)}
                  </p>
                  <p>
                    <span className="font-semibold">Productivity:</span>{" "}
                    {currentActivity.productivity_score}/10
                  </p>

                  <div className="pt-2 border-t">
                    <p className="font-semibold mb-1">AI Response:</p>
                    <pre className="text-xs bg-gray-100 p-3 rounded-md whitespace-pre-wrap break-words">
                      {JSON.stringify(currentActivity.aiAnalysis, null, 2) ||
                        "No AI analysis"}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  </div>
);
}
