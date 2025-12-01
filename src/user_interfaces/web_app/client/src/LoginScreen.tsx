
import React, { useState } from "react";
import "./App.css";
import "./LoginScreen.css";

// Base URL for backend auth endpoints (set with Vite env var VITE_API_BASE)
const API_BASE = import.meta.env.VITE_API_BASE || "";

interface LoginScreenProps {
  onSuccess: () => void;
}

export function LoginScreen({ onSuccess }: LoginScreenProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch(`${API_BASE}/auth/google/url`);
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      if (data && data.url) {
        // Redirect browser to Google OAuth URL
        window.location.href = data.url;
      } else {
        throw new Error("No URL returned from auth endpoint");
      }
    } catch (err: any) {
      console.error("Google login failed", err);
      setError(err?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-form">
        <div className="login-logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#007acc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        </div>
        <h2 className="login-title">Welcome</h2>
        <p className="login-desc">Sign in with your Google account to continue</p>
        <button
          className="login-btn"
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
        >
          {loading ? "Connecting..." : "Continue with Google"}
        </button>
        {error && <div className="login-error">{error}</div>}
      </div>
    </div>
  );
}
