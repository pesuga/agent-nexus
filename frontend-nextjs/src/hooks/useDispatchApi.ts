"use client";

import { useCallback } from "react";
import { Task, Agent, AgentProfile, ModelRecord } from "@/types/dispatch";

export function useDispatchApi() {
  const apiFetch = useCallback(async <T>(endpoint: string, options: RequestInit = {}) => {
    const resp = await fetch(`/api/dispatch/${endpoint.replace(/^\/api\//, "")}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (resp.status === 401) {
      // Force logout on 401
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(error.detail || `API Error: ${resp.status}`);
    }

    return resp.json() as Promise<T>;
  }, []);

  const fetchTasks = useCallback(async (projectId: string) => {
    return apiFetch<Task[]>(`/api/tasks?project_id=${encodeURIComponent(projectId)}`);
  }, [apiFetch]);

  const updateTask = useCallback(async (taskId: string, updates: Partial<Task>) => {
    return apiFetch<Task>(`/api/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  }, [apiFetch]);

  const createTask = useCallback(async (task: Partial<Task>) => {
    return apiFetch<Task>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(task),
    });
  }, [apiFetch]);

  const deleteTask = useCallback(async (taskId: string) => {
    return apiFetch<{ ok?: boolean }>(`/api/tasks/${taskId}`, {
      method: "DELETE",
    });
  }, [apiFetch]);

  const fetchAgents = useCallback(async () => {
    return apiFetch<Agent[]>("/api/agents");
  }, [apiFetch]);

  const fetchAgentProfiles = useCallback(async (projectId: string) => {
    return apiFetch<AgentProfile[]>(`/api/projects/${projectId}/agent-profiles`);
  }, [apiFetch]);

  const createAgentProfile = useCallback(async (projectId: string, profile: Partial<AgentProfile>) => {
    return apiFetch<AgentProfile>(`/api/projects/${projectId}/agent-profiles`, {
      method: "POST",
      body: JSON.stringify(profile),
    });
  }, [apiFetch]);

  const updateAgentProfile = useCallback(async (profileId: string, updates: Partial<AgentProfile>) => {
    return apiFetch<AgentProfile>(`/api/agent-profiles/${profileId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  }, [apiFetch]);

  const deleteAgentProfile = useCallback(async (profileId: string) => {
    return apiFetch<{ ok?: boolean }>(`/api/agent-profiles/${profileId}`, {
      method: "DELETE",
    });
  }, [apiFetch]);

  const fetchModels = useCallback(async () => {
    return apiFetch<ModelRecord[]>("/api/models");
  }, [apiFetch]);

  const estimateContext = useCallback(async (taskId: string, params: Partial<{
    comments_limit: number;
    artifacts_limit: number;
    activity_limit: number;
  }> = {}) => {
    return apiFetch<{
      estimated_tokens: Record<string, number>;
      total_estimated_tokens: number;
    }>(`/api/tasks/${taskId}/context/estimate`, {
      method: "POST",
      body: JSON.stringify({
        comments_limit: 20,
        artifacts_limit: 20,
        activity_limit: 30,
        ...params
      }),
    });
  }, [apiFetch]);

  return {
    fetchTasks,
    updateTask,
    createTask,
    deleteTask,
    fetchAgents,
    fetchAgentProfiles,
    createAgentProfile,
    updateAgentProfile,
    deleteAgentProfile,
    fetchModels,
    estimateContext,
  };
}
