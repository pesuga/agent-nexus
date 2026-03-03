"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { UIConfig, Project, AuthSession } from "@/types/dispatch";

interface AppContextType {
  config: UIConfig;
  setConfig: (config: UIConfig) => void;
  user: AuthSession | null;
  setUser: (user: AuthSession | null) => void;
  projects: Project[];
  currentProjectId: string;
  setCurrentProjectId: (id: string) => void;
  refreshProjects: () => Promise<void>;
  logout: () => Promise<void>;
}

const UI_CONFIG_KEY = 'dispatch_ui_config_v1';
const CURRENT_PROJECT_KEY = "dispatch_current_project_v1";

const DEFAULT_CONFIG: UIConfig = {
  apiBaseUrl: 'http://localhost:8000',
  actorRole: 'human_admin',
  actorId: 'frontend-ui',
  apiToken: '',
};

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfigState] = useState<UIConfig>(DEFAULT_CONFIG);
  const [user, setUserState] = useState<AuthSession | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProjectId, setCurrentProjectIdState] = useState<string>("pesulabs");
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const savedConfig = localStorage.getItem(UI_CONFIG_KEY);
    const savedProjectId = localStorage.getItem(CURRENT_PROJECT_KEY);
    if (savedConfig) {
      try {
        setConfigState({ ...DEFAULT_CONFIG, ...JSON.parse(savedConfig) });
      } catch (e) {
        console.error("Failed to parse saved config", e);
      }
    }
    if (savedProjectId) {
      setCurrentProjectIdState(savedProjectId);
    }

    // Fetch session from cookie-based API
    fetch("/api/auth/me")
      .then(res => res.ok ? res.json() : null)
      .then(session => {
        if (session) {
          setUserState(session);
        }
        setInitialized(true);
      })
      .catch(() => setInitialized(true));
  }, []);

  const setConfig = (newConfig: UIConfig) => {
    setConfigState(newConfig);
    localStorage.setItem(UI_CONFIG_KEY, JSON.stringify(newConfig));
  };

  const setCurrentProjectId = (id: string) => {
    setCurrentProjectIdState(id);
    localStorage.setItem(CURRENT_PROJECT_KEY, id);
  };

  const setUser = (newUser: AuthSession | null) => {
    setUserState(newUser);
    if (newUser) {
      // Update config with user info for backward compatibility
      setConfig({
        ...config,
        actorId: newUser.actor_id,
        actorRole: newUser.actor_role,
      });
    }
  };

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setUserState(null);
    window.location.href = '/login';
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      const headers: Record<string, string> = {
        'X-Actor-Role': user?.actor_role || config.actorRole,
        'X-Actor-Id': user?.actor_id || config.actorId,
        'X-API-Token': config.apiToken,
      };

      const resp = await fetch(`${config.apiBaseUrl}/api/projects`, {
        headers
      });
      if (resp.ok) {
        const data: Project[] = await resp.json();
        // Temporary cleanup: focus UI on pesulabs until full multi-project UX is finalized.
        const filtered = data.filter(
          (project) =>
            project.id.toLowerCase() === "pesulabs" ||
            project.name.toLowerCase() === "pesulabs"
        );
        const finalProjects = filtered.length > 0 ? filtered : data;
        setProjects(finalProjects);

        const hasCurrent = finalProjects.some((project) => project.id === currentProjectId);
        if (!hasCurrent && finalProjects.length > 0) {
          const preferred =
            finalProjects.find(
              (project) =>
                project.id.toLowerCase() === "pesulabs" ||
                project.name.toLowerCase() === "pesulabs"
            ) || finalProjects[0];
          setCurrentProjectId(preferred.id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch projects", e);
    }
  }, [config, user, currentProjectId]);

  useEffect(() => {
    if (initialized && user) {
      refreshProjects();
    }
  }, [initialized, user, refreshProjects]);

  if (!initialized) {
    return null; // Or a loading spinner
  }

  return (
    <AppContext.Provider
      value={{
        config,
        setConfig,
        user,
        setUser,
        projects,
        currentProjectId,
        setCurrentProjectId,
        refreshProjects,
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
