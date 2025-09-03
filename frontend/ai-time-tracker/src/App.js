import React, { useState, useEffect } from "react";
import {
  Clock,
  Activity,
  Users,
  BarChart3,
  Eye,
  Zap,
} from "lucide-react";
import { useAuth } from "./AuthContext";
import ManualEntryForm from "./components/ManualEntryForm";
import { BASE_URL } from "./config";

const AITimeTracker = () => {
  const { authFetch } = useAuth();
  const [activities, setActivities] = useState([]);
  const [currentActivity, setCurrentActivity] = useState(null);
  const [isTracking, setIsTracking] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [summary, setSummary] = useState({
    totalTime: 0,
    productiveTime: 0,
    clientsWorkedWith: 0,
    averageProductivity: 0,
  });
  const [loading, setLoading] = useState(true);

  // Fetch activities from backend
  const fetchActivities = async (date) => {
    setLoading(true);
    try {
      const response = await authFetch(
        `${BASE_URL}/api/activities?date=${date}`
      );
      if (!response) return;
      const data = await response.json();
      setActivities(data);
      calculateSummary(data);
    } catch (error) {
      console.error("Error fetching activities:", error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate daily summary
  const calculateSummary = (activities) => {
    let totalTime = activities.reduce(
      (sum, activity) => sum + (activity.duration_minutes || 0),
      0
    );
    let productiveTime = activities
      .filter((activity) => activity.productivity_score >= 7)
      .reduce((sum, activity) => sum + (activity.duration_minutes || 0), 0);

    if (totalTime > 1440) totalTime = 1440;
    if (productiveTime > 1440) productiveTime = 1440;

    const uniqueClients = new Set(
      activities
        .map((activity) => activity.client_identified)
        .filter((client) => client && client !== "None")
    );

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

  // Fetch tracking status from backend
const fetchTrackingStatus = async () => {
  try {
    const response = await authFetch(`${BASE_URL}/api/tracking-status`);
    if (response && response.ok) {
      const data = await response.json();
      setIsTracking(data.is_tracking);
    }
  } catch (error) {
    console.error("Error fetching tracking status:", error);
  }
};


  // Start/Stop tracking
  const toggleTracking = async () => {
    try {
      const endpoint = isTracking
        ? `${BASE_URL}/api/stop-tracking`
        : `${BASE_URL}/api/start-tracking`;

      const response = await authFetch(endpoint, {
        method: "POST",
      });

      if (response && response.ok) {
        setIsTracking(!isTracking);
      }
    } catch (error) {
      console.error("Error toggling tracking:", error);
    }
  };

  useEffect(() => {
    fetchTrackingStatus();   // ✅ run once when app loads
    fetchActivities(selectedDate);
  }, [selectedDate]);

  // Utils
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
    if (score >= 8)
      return "bg-green-100 text-green-800 border-green-300";
    if (score >= 6)
      return "bg-yellow-100 text-yellow-800 border-yellow-300";
    if (score >= 4)
      return "bg-orange-100 text-orange-800 border-orange-300";
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Clock className="text-blue-600" />
                AI Time Tracker
              </h1>
              <p className="text-gray-600 mt-1">
                Intelligent activity monitoring with client detection
              </p>
            </div>

            <div className="flex items-center gap-4">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={toggleTracking}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  isTracking
                    ? "bg-red-500 hover:bg-red-600 text-white"
                    : "bg-blue-500 hover:bg-blue-600 text-white"
                }`}
              >
                {isTracking ? "⏹️ Stop Tracking" : "▶️ Start Tracking"}
              </button>

              <button
                onClick={() => setShowManualForm(true)}
                className="px-6 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg"
              >
                ✍️ Manual Entry
              </button>

              <button
                onClick={() => {
                  localStorage.removeItem("token");
                  window.location.href = "/login";
                }}
                className="px-4 py-2 bg-red-600 rounded-lg hover:bg-red-800 text-white"
              >
                Logout
              </button>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Time</p>
                <p className="text-2xl font-bold text-gray-900">
                  {summary.totalTime}h
                </p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Productive Time
                </p>
                <p className="text-2xl font-bold text-green-600">
                  {summary.productiveTime}h
                </p>
              </div>
              <Zap className="w-8 h-8 text-green-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Clients</p>
                <p className="text-2xl font-bold text-purple-600">
                  {summary.clientsWorkedWith}
                </p>
              </div>
              <Users className="w-8 h-8 text-purple-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Avg Productivity
                </p>
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
              <BarChart3 className="w-8 h-8 text-orange-500" />
            </div>
          </div>
        </div>

        {/* Activities List */}
        <div className="bg-white rounded-lg shadow-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Activities for {selectedDate}
            </h2>
          </div>

          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-4 animate-spin opacity-50" />
                <p>Loading activities...</p>
              </div>
            ) : activities.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No activities recorded for this date</p>
              </div>
            ) : (
              activities.map((activity) => {
                let aiAnalysis = {};
                if (typeof activity.ai_analysis === "string") {
                  try {
                    aiAnalysis = JSON.parse(activity.ai_analysis);
                  } catch {
                    aiAnalysis = {};
                  }
                } else if (
                  typeof activity.ai_analysis === "object" &&
                  activity.ai_analysis !== null
                ) {
                  aiAnalysis = activity.ai_analysis;
                }

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
                          {new Date(
                            activity.start_time
                          ).toLocaleTimeString()}{" "}
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

        {/* Manual Entry Modal */}
        {showManualForm && (
          <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
            <div className="bg-white rounded-xl shadow-2xl w-[90%] max-w-lg max-h-[80vh] overflow-y-auto p-6 relative">
              <button
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
                onClick={() => setShowManualForm(false)}
              >
                ✖
              </button>
              <ManualEntryForm
                onEntryAdded={() => {
                  setShowManualForm(false);
                  fetchActivities(selectedDate);
                }}
              />
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
      </div>
    </div>
  );
};

export default AITimeTracker;
