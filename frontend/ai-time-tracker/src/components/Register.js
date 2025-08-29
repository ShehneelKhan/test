import React, { useState } from "react";
import { BASE_URL } from "../config"; // ✅ import the BASE_URL

const Register = () => {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [message, setMessage] = useState("");

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${BASE_URL}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, role: "employee" }),
      });

      if (res.ok) {
        setMessage("✅ Registered successfully! Now login.");
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
        <h2 className="text-2xl font-bold mb-4 text-center">Register</h2>
        <input name="name" placeholder="Name" onChange={handleChange} className="w-full p-2 mb-3 border rounded" />
        <input name="email" type="email" placeholder="Email" onChange={handleChange} className="w-full p-2 mb-3 border rounded" />
        <input name="password" type="password" placeholder="Password" onChange={handleChange} className="w-full p-2 mb-3 border rounded" />
        <button className="w-full bg-blue-500 text-white p-2 rounded">Register</button>
        {message && <p className="mt-2 text-sm">{message}</p>}
      </form>
    </div>
  );
};

export default Register;
