// src/components/ClientForm.jsx
import React, { useState, useEffect } from "react";
import { BASE_URL } from "../config";
import { useAuth } from "../AuthContext";

const ClientForm = ({ client, onSuccess, onCancel }) => {
  const [name, setName] = useState(client ? client.name : "");
  const [contactEmail, setContactEmail] = useState(client ? client.contact_email : "");
  const [loading, setLoading] = useState(false);
  const { authFetch } = useAuth();

  useEffect(() => {
    if (client) {
      setName(client.name);
      setContactEmail(client.contact_email);
    }
  }, [client]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const method = client ? "PUT" : "POST";
    const url = client ? `${BASE_URL}/api/clients/${client.id}` : `${BASE_URL}/api/clients`;

    const response = await authFetch(url, {
      method,
      body: JSON.stringify({ name, contact_email: contactEmail }),
    });

    setLoading(false);

    if (response && response.ok) {
      const data = await response.json();
      onSuccess(data);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <h2 className="text-lg font-bold mb-4">
        {client ? "Edit Client" : "Add Client"}
      </h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="block text-sm font-medium">Name</label>
          <input
            className="w-full border px-3 py-2 rounded-md"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="mb-3">
          <label className="block text-sm font-medium">Contact Email</label>
          <input
            className="w-full border px-3 py-2 rounded-md"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            required
          />
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded-md"
          >
            {loading ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="bg-gray-300 px-4 py-2 rounded-md"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default ClientForm;
