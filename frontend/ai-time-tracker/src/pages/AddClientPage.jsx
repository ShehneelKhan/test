// src/pages/AddClientPage.jsx
import React, { useState } from "react";
import AddClientForm from "../components/AddClientForm"; // ✅ adjust path if needed
import { useNavigate } from "react-router-dom";

export default function AddClientPage() {
  const [clients, setClients] = useState([]);
  const navigate = useNavigate();

  const handleClientAdded = (newClient) => {
    setClients((prev) => [...prev, newClient]);
    navigate("/admin"); // ✅ go back to AdminDashboard after adding
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
        <AddClientForm onClientAdded={handleClientAdded} />
      </div>
    </div>
  );
}
