// src/components/ClientList.jsx
import React, { useEffect, useState } from "react";
import { BASE_URL } from "../config";
import { useAuth } from "../AuthContext";
import ClientForm from "./ClientForm";

const ClientList = () => {
  const { authFetch } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingClient, setEditingClient] = useState(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    setLoading(true);
    const response = await authFetch(`${BASE_URL}/api/clients`);
    if (response && response.ok) {
      const data = await response.json();
      setClients(data);
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this client?")) return;
    const response = await authFetch(`${BASE_URL}/api/clients/${id}`, {
      method: "DELETE",
    });
    if (response && response.ok) {
      setClients(clients.filter((c) => c.id !== id));
    }
  };

  const handleSave = (client) => {
    if (editingClient) {
      // update existing client
      setClients(clients.map((c) => (c.id === client.id ? client : c)));
      setEditingClient(null);
    } else {
      // add new client
      setClients([...clients, client]);
      setAdding(false);
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Client Management</h1>
        <button
          onClick={() => setAdding(true)}
          className="bg-green-500 text-white px-4 py-2 rounded-md"
        >
          + Add Client
        </button>
      </div>

      {loading ? (
        <p>Loading clients...</p>
      ) : (
        <table className="w-full border rounded-md bg-white shadow-md">
          <thead className="bg-gray-100">
            <tr>
              <th className="p-2 border">ID</th>
              <th className="p-2 border">Name</th>
              <th className="p-2 border">Email</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td className="p-2 border">{client.id}</td>
                <td className="p-2 border">{client.name}</td>
                <td className="p-2 border">{client.contact_email}</td>
                <td className="p-2 border flex gap-2">
                  <button
                    onClick={() => setEditingClient(client)}
                    className="bg-blue-500 text-white px-3 py-1 rounded"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(client.id)}
                    className="bg-red-500 text-white px-3 py-1 rounded"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {clients.length === 0 && (
              <tr>
                <td colSpan="4" className="text-center p-4">
                  No clients found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {/* Show add/edit form */}
      {(adding || editingClient) && (
        <div className="mt-6">
          <ClientForm
            client={editingClient}
            onSuccess={handleSave}
            onCancel={() => {
              setAdding(false);
              setEditingClient(null);
            }}
          />
        </div>
      )}
    </div>
  );
};

export default ClientList;
