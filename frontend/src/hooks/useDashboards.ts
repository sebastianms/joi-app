"use client";

import { useCallback, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export interface DashboardItem {
  id: string;
  widget_id: string;
  display_name: string;
  grid_x: number;
  grid_y: number;
  width: number;
  height: number;
  z_order: number;
}

export interface Dashboard {
  id: string;
  session_id: string;
  name: string;
  items: DashboardItem[];
}

export interface LayoutItemUpdate {
  widget_id: string;
  grid_x: number;
  grid_y: number;
  width: number;
  height: number;
  z_order?: number;
}

export interface AddItemPayload {
  session_id: string;
  widget_id: string;
  grid_x?: number;
  grid_y?: number;
  width?: number;
  height?: number;
}

export interface UseDashboardsResult {
  dashboards: Dashboard[];
  currentDashboard: Dashboard | null;
  isLoading: boolean;
  error: string | null;
  fetchDashboards: (sessionId: string) => Promise<void>;
  fetchDashboard: (id: string, sessionId: string) => Promise<void>;
  createDashboard: (sessionId: string, name: string) => Promise<Dashboard | null>;
  renameDashboard: (id: string, sessionId: string, name: string) => Promise<boolean>;
  deleteDashboard: (id: string, sessionId: string) => Promise<boolean>;
  updateLayout: (id: string, sessionId: string, items: LayoutItemUpdate[]) => Promise<boolean>;
  addItem: (dashboardId: string, payload: AddItemPayload) => Promise<DashboardItem | null>;
  removeItem: (dashboardId: string, widgetId: string, sessionId: string) => Promise<boolean>;
}

export function useDashboards(): UseDashboardsResult {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [currentDashboard, setCurrentDashboard] = useState<Dashboard | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboards = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/dashboards?session_id=${encodeURIComponent(sessionId)}`);
      if (!res.ok) throw new Error(`Failed to fetch dashboards: ${res.status}`);
      setDashboards(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchDashboard = useCallback(async (id: string, sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/dashboards/${id}?session_id=${encodeURIComponent(sessionId)}`,
      );
      if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
      setCurrentDashboard(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createDashboard = useCallback(
    async (sessionId: string, name: string): Promise<Dashboard | null> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/dashboards`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, name }),
        });
        if (!res.ok) throw new Error(`Failed to create dashboard: ${res.status}`);
        const created: Dashboard = await res.json();
        setDashboards((prev) => [...prev, created]);
        return created;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return null;
      }
    },
    [],
  );

  const renameDashboard = useCallback(
    async (id: string, sessionId: string, name: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/dashboards/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, name }),
        });
        if (!res.ok) throw new Error(`Failed to rename dashboard: ${res.status}`);
        const updated: Dashboard = await res.json();
        setDashboards((prev) => prev.map((d) => (d.id === id ? { ...d, name: updated.name } : d)));
        setCurrentDashboard((prev) => (prev?.id === id ? { ...prev, name: updated.name } : prev));
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const deleteDashboard = useCallback(
    async (id: string, sessionId: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/dashboards/${id}?session_id=${encodeURIComponent(sessionId)}`,
          { method: "DELETE" },
        );
        if (!res.ok) throw new Error(`Failed to delete dashboard: ${res.status}`);
        setDashboards((prev) => prev.filter((d) => d.id !== id));
        setCurrentDashboard((prev) => (prev?.id === id ? null : prev));
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const updateLayout = useCallback(
    async (id: string, sessionId: string, items: LayoutItemUpdate[]): Promise<boolean> => {
      // Optimistic update
      setCurrentDashboard((prev) => {
        if (!prev || prev.id !== id) return prev;
        const updated = items.reduce<Record<string, LayoutItemUpdate>>(
          (acc, it) => ({ ...acc, [it.widget_id]: it }),
          {},
        );
        return {
          ...prev,
          items: prev.items.map((item) =>
            updated[item.widget_id] ? { ...item, ...updated[item.widget_id] } : item,
          ),
        };
      });
      try {
        const res = await fetch(`${API_URL}/dashboards/${id}/layout`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, items }),
        });
        if (!res.ok) throw new Error(`Failed to update layout: ${res.status}`);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const addItem = useCallback(
    async (dashboardId: string, payload: AddItemPayload): Promise<DashboardItem | null> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/dashboards/${dashboardId}/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Failed to add item: ${res.status}`);
        const item: DashboardItem = await res.json();
        setCurrentDashboard((prev) =>
          prev?.id === dashboardId ? { ...prev, items: [...prev.items, item] } : prev,
        );
        return item;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return null;
      }
    },
    [],
  );

  const removeItem = useCallback(
    async (dashboardId: string, widgetId: string, sessionId: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/dashboards/${dashboardId}/items/${widgetId}?session_id=${encodeURIComponent(sessionId)}`,
          { method: "DELETE" },
        );
        if (!res.ok) throw new Error(`Failed to remove item: ${res.status}`);
        setCurrentDashboard((prev) =>
          prev?.id === dashboardId
            ? { ...prev, items: prev.items.filter((i) => i.widget_id !== widgetId) }
            : prev,
        );
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  return {
    dashboards,
    currentDashboard,
    isLoading,
    error,
    fetchDashboards,
    fetchDashboard,
    createDashboard,
    renameDashboard,
    deleteDashboard,
    updateLayout,
    addItem,
    removeItem,
  };
}
