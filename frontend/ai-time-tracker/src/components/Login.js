import React, { useState } from "react";
import { useAuth } from "../AuthContext";
import { BASE_URL } from "../config"; // ✅ import the BASE_URL

const Login = () => {
  const { login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [message, setMessage] = useState("");

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${BASE_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        const data = await res.json();
        login(data.access_token, { role: data.role }); // ✅ save role too
        setMessage("✅ Login successful!");
        window.location.href = "/"; // Redirect to dashboard
      } else {
        const err = await res.json();
        setMessage("❌ " + err.detail);
      }
    } catch (error) {
      setMessage("❌ Something went wrong.");
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow-md w-96">
        <h2 className="text-2xl font-bold mb-4 text-center">Login</h2>
        <input name="username" placeholder="Email" onChange={handleChange} className="w-full p-2 mb-3 border rounded" />
        <input name="password" type="password" placeholder="Password" onChange={handleChange} className="w-full p-2 mb-3 border rounded" />
        <button className="w-full bg-blue-500 hover:bg-blue-800 text-white p-2 rounded">Login</button>
        {message && <p className="mt-2 text-sm">{message}</p>}
      </form>
    </div>
  );
};

export default Login;
