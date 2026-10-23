"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./auth-context";
import { api, type BankPositionOut, type NotificationOut } from "./api";

interface StaffState {
  positions: BankPositionOut[];
  position: BankPositionOut | null;
  loading: boolean;
  notifications: NotificationOut[];
  unreadCount: number;
  refreshNotifications: () => void;
  markNotificationRead: (id: string) => Promise<void>;
}

const StaffContext = createContext<StaffState | undefined>(undefined);

export function StaffProvider({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuth();
  const [positions, setPositions] = useState<BankPositionOut[]>([]);
  const [notifications, setNotifications] = useState<NotificationOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshNotifications = useCallback(() => {
    if (!token) return;
    api.notifications(token).then(setNotifications).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([api.bankPositions(token), api.notifications(token)])
      .then(([p, n]) => {
        setPositions(p);
        setNotifications(n);
      })
      .catch(() => {
        setPositions([]);
        setNotifications([]);
      })
      .finally(() => setLoading(false));
  }, [token]);

  async function markNotificationRead(id: string) {
    if (!token) return;
    const updated = await api.markNotificationRead(token, id);
    setNotifications((ns) => ns.map((n) => (n.id === id ? updated : n)));
  }

  const position = positions.find((p) => p.id === user?.position_id) ?? null;
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <StaffContext.Provider
      value={{ positions, position, loading, notifications, unreadCount, refreshNotifications, markNotificationRead }}
    >
      {children}
    </StaffContext.Provider>
  );
}

export function useStaff() {
  const ctx = useContext(StaffContext);
  if (!ctx) throw new Error("useStaff must be used inside StaffProvider");
  return ctx;
}
