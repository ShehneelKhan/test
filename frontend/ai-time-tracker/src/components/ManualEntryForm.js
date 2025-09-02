import React, { useState, useEffect } from "react";
import { useAuth } from "../AuthContext";
import { BASE_URL } from "../config"; // ✅ import the BASE_URL

export default function ManualEntryForm({ onEntryAdded }) {
  const { authFetch } = useAuth();
  const [clients, setClients] = useState([]);
  const [error, setError] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  const [form, setForm] = useState({
    clientName: "",
    description: "",
    application: "",
    duration: "",
    date: new Date().toISOString().split("T")[0],
    startTime: "09:00",
    status: "In Progress",
  });

  useEffect(() => {
    const fetchClients = async () => {
      const res = await authFetch(`${BASE_URL}/api/clients`);
      if (!res) return; // logged out
      const data = await res.json();
      setClients(data);
    };
    fetchClients();
  }, [authFetch]);

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.description || !form.application || !form.duration) {
        setPopupMessage("⚠️ Please fill in all required fields.");
        return;
    }
    setPopupMessage("");

    const res = await authFetch(`${BASE_URL}/api/manual-entry`, {
        method: "POST",
        body: JSON.stringify(form),
    });

    if (res) {
        if (res.ok) {
        onEntryAdded();
        setForm({
            clientName: "",
            description: "",
            application: "",
            project_task: "",
            duration: "",
            date: new Date().toISOString().split("T")[0],
            startTime: "09:00",
            status: "In Progress",
        });
        setPopupMessage("✅ Entry created successfully!");
        } else {
        const errData = await res.json();
        setPopupMessage(errData.detail || "Something went wrong. Please try again.");
        }
    }
    };



  return (
  <>
    {/* Popup Component */}
    {popupMessage && (
      <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full">
          <p className="mb-4 text-gray-800">{popupMessage}</p>
          <button
            onClick={() => setPopupMessage("")}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg w-full"
          >
            OK
          </button>
        </div>
      </div>
    )}

    {/* Your Form */}
    <form
      onSubmit={handleSubmit}
      className="bg-white shadow rounded-lg p-6 mb-6"
    >
      <h2 className="text-3xl font-bold text-blue-600 mb-4">Manual Time Entry</h2>
      <br></br>

      {/* you can keep inline error if you want, or remove since popup is handling */}
      {error && <p className="text-red-600 mb-3">{error}</p>}

      {/* Client Selection */}
      <label className="block mb-2 text-sm font-medium">Client *</label>
      <select
        value={form.clientName}
        onChange={(e) => setForm({ ...form, clientName: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
      >
        <option value="">Select Client</option>
        {clients.map((c) => (
          <option key={c.id} value={c.name}>
            {c.name}
          </option>
        ))}
      </select>

      {/* Description */}
      <label className="block mb-2 text-sm font-medium">Description *</label>
      <input
        type="text"
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />

      {/* Application */}
      <label className="block mb-2 text-sm font-medium">Application *</label>
      <input
        type="text"
        value={form.application}
        onChange={(e) => setForm({ ...form, application: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />

      {/* Project or Task */}
      <label className="block mb-2 text-sm font-medium">Project / Task *</label>
      <input
        type="text"
        value={form.project_task}
        onChange={(e) => setForm({ ...form, project_task: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />

      {/* Duration */}
      <label className="block mb-2 text-sm font-medium">Duration (hours) *</label>
      <input
        type="number"
        step="0.25"
        min="0.25"
        value={form.duration}
        onChange={(e) => {
          const value = parseFloat(e.target.value);
          if (value > 0) {
            setForm({ ...form, duration: value });
          } else {
            setForm({ ...form, duration: "" });
          }
        }}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />

      {/* Date */}
      <label className="block mb-2 text-sm font-medium">Date *</label>
      <input
        type="date"
        value={form.date}
        min={new Date().toISOString().split("T")[0]}   // ✅ only today
        max={new Date().toISOString().split("T")[0]}   // ✅ only today
        onChange={(e) => setForm({ ...form, date: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />


      {/* Start Time */}
      <label className="block mb-2 text-sm font-medium">Start Time *</label>
      <input
        type="time"
        value={form.startTime}
        onChange={(e) => setForm({ ...form, startTime: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
        required
      />

      {/* Status */}
      <label className="block mb-2 text-sm font-medium">Status</label>
      <select
        value={form.status}
        onChange={(e) => setForm({ ...form, status: e.target.value })}
        className="w-full border rounded-lg p-2 mb-4"
      >
        <option>In Progress</option>
        <option>Completed</option>
      </select>

      <button
        type="submit"
        className="bg-blue-600 text-white px-4 py-2 rounded-lg"
      >
        + Generate Entry
      </button>
    </form>
  </>
);

}
