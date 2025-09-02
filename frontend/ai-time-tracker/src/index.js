import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import Login from "./components/Login";
import Register from "./components/Register";
import ManualEntryForm from "./components/ManualEntryForm";
import ProtectedRoute from "./ProtectedRoute";
import { AuthProvider } from "./AuthContext";
import AdminDashboard from "./pages/AdminDashboard";
import WeeklyReport from "./pages/WeeklyReport";
import AddClientPage from "./pages/AddClientPage"; // ✅ new import
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <AuthProvider>
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected user dashboard */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <App />
            </ProtectedRoute>
          }
        />

        {/* Manual entry (protected) */}
        <Route
          path="/manual-entry"
          element={
            <ProtectedRoute>
              <ManualEntryForm onEntryAdded={() => (window.location.href = "/")} />
            </ProtectedRoute>
          }
        />

        {/* Admin dashboard (protected) */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />

        {/* Add Client page (protected) */}
        <Route
          path="/admin/add-client"
          element={
            <ProtectedRoute>
              <AddClientPage />
            </ProtectedRoute>
          }
        />

        {/* Admin weekly report (protected) */}
        <Route
          path="/admin/weekly-report/:id"
          element={
            <ProtectedRoute>
              <WeeklyReport />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  </AuthProvider>
);
