import React from "react";
import { Navigate, useLocation } from "react-router-dom";

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("token");
  const user = JSON.parse(localStorage.getItem("user")); // { role, is_admin }
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Admin access control
  if (user?.role === "admin" || user?.is_admin) {
    if (location.pathname === "/") {
      return <Navigate to="/admin" replace />;
    }
  }

  // Employee access control
  if (user?.role === "employee" && location.pathname.startsWith("/admin")) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;
