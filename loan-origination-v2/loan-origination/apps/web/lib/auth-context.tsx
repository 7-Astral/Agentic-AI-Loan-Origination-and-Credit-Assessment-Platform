"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type UserOut } from "./api";

interface AuthState {
  token: string | null;
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserOut>;
  register: (email: string, password: string, fullName: string) => Promise<UserOut>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("lo_token") : null;
    if (stored) {
      setToken(stored);
      api
        .me(stored)
        .then(setUser)
        .catch(() => {
          window.localStorage.removeItem("lo_token");
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  async function login(email: string, password: string) {
    const res = await api.login(email, password);
    window.localStorage.setItem("lo_token", res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }

  async function register(email: string, password: string, fullName: string) {
    const res = await api.register(email, password, fullName);
    window.localStorage.setItem("lo_token", res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }

  function logout() {
    window.localStorage.removeItem("lo_token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
