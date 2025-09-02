import React, { useState } from "react";
import { BASE_URL } from "../config"; // ✅ import the BASE_URL

const AddClientForm = ({ onClientAdded }) => {
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Retrieve the token from localStorage
      const token = localStorage.getItem("token");
      console.log("Retrieved token:", token);

      if (!token) {
        setError("No token found, please login again.");
        setLoading(false);
        return;
      }

      const payload = { name, contact_email: contactEmail };
      const headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      };

      console.log("Request headers:", headers);
      console.log("Request body:", payload);

      // Send request
      const response = await fetch(`${BASE_URL}/api/clients`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Response error text:", errorText);
        throw new Error(`Error adding client: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      console.log("Response JSON:", data);

      onClientAdded(data);

      // Reset form
      setName("");
      setContactEmail("");
    } catch (error) {
      console.error("Caught error:", error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white p-4 rounded-lg shadow-md">
      <h2 className="text-xl font-bold mb-4">Add New Client</h2>
      {error && <p className="text-red-500">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            Client Name
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            required
          />
        </div>
        <div className="mb-4">
          <label htmlFor="contactEmail" className="block text-sm font-medium text-gray-700">
            Contact Email
          </label>
          <input
            id="contactEmail"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-500 text-white py-2 rounded-md mt-4"
        >
          {loading ? "Adding..." : "+ Add Client"}
        </button>
      </form>
    </div>
  );
};

export default AddClientForm;
