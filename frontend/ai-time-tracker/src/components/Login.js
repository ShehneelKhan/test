import React, { useState } from "react";
import { useAuth } from "../AuthContext";
import { BASE_URL } from "../config";

const Login = () => {
  const { login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [errorDialog, setErrorDialog] = useState("");

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorDialog("");

    try {
      const res = await fetch(`${BASE_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        const data = await res.json();

        // Save token + role
        login(data.access_token, { role: data.role, is_admin: data.is_admin });

        // Redirect based on role
        if (data.role === "admin" || data.is_admin === true) {
          window.location.href = "/admin";
        } else {
          window.location.href = "/";
        }
      } else {
        const err = await res.json();
        setErrorDialog(err.detail || "Invalid credentials");
      }
    } catch (error) {
      setErrorDialog("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-6 rounded shadow-md w-96"
      >
        <h2 className="text-2xl font-bold mb-4 text-center">Login</h2>

        <input
          name="username"
          placeholder="Email"
          onChange={handleChange}
          className="w-full p-2 mb-3 border rounded"
          required
        />
        <input
          name="password"
          type="password"
          placeholder="Password"
          onChange={handleChange}
          className="w-full p-2 mb-3 border rounded"
          required
        />

        <button
          type="submit"
          disabled={loading}
          className={`w-full flex justify-center items-center bg-blue-500 hover:bg-blue-800 text-white p-2 rounded ${
            loading ? "opacity-70 cursor-not-allowed" : ""
          }`}
        >
          {loading ? (
            <svg
              className="animate-spin h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              ></path>
            </svg>
          ) : (
            "Login"
          )}
        </button>

        {/* ✅ Always show register link */}
        <p className="mt-4 text-sm text-center text-gray-600">
          Create an account?{" "}
          <a href="/register" className="text-blue-600 hover:underline">
            Register
          </a>
        </p>


      </form>

      {/* Error Dialog */}
      {errorDialog && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white p-6 rounded shadow-md max-w-sm w-full">
            <h3 className="text-lg font-semibold mb-2 text-red-600">Login Failed</h3>
            <p className="text-gray-700 mb-4">{errorDialog}</p>
            <button
              onClick={() => setErrorDialog("")}
              className="bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded"
            >
              Close
            </button>

          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
