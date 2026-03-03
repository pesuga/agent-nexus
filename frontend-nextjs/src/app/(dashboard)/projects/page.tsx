"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";
import { Project } from "@/types/dispatch";
import { IconPlus, IconFolder, IconSettings, IconUsers } from "@tabler/icons-react";

export default function ProjectsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const [newProject, setNewProject] = useState({
    name: "",
    description: ""
  });

  const { config, user, projects, refreshProjects, setCurrentProjectId, currentProjectId } = useAppContext();

  useEffect(() => {
    refreshProjects().finally(() => setLoading(false));
  }, [refreshProjects]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify(newProject)
      });
      if (resp.ok) {
        setShowCreateModal(false);
        setNewProject({ name: "", description: "" });
        refreshProjects();
      } else {
        const data = await resp.json();
        alert(data.detail || "Failed to create project");
      }
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  if (loading) return <div>Loading projects...</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header d-print-none">
        <div className="container-xl">
          <div className="row g-2 align-items-center">
            <div className="col">
              <h2 className="page-title">
                Projects
              </h2>
            </div>
            {user?.actor_role === 'human_admin' && (
              <div className="col-auto ms-auto d-print-none">
                <div className="btn-list">
                  <button 
                    className="btn btn-primary d-none d-sm-inline-block"
                    onClick={() => setShowCreateModal(true)}
                  >
                    <IconPlus size={18} />
                    Create new project
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="container-xl">
          <div className="row row-cards">
            {projects.map((p) => (
              <div key={p.id} className="col-md-6 col-lg-4">
                <div className={`card ${currentProjectId === p.id ? 'border-primary' : ''}`}>
                  <div className="card-body">
                    <div className="d-flex align-items-center mb-3">
                      <span className="avatar avatar-md bg-primary-lt">
                        <IconFolder size={24} />
                      </span>
                      <div className="ms-3">
                        <h3 className="card-title mb-0">{p.name}</h3>
                        <div className="text-muted small">ID: {p.id}</div>
                      </div>
                    </div>
                    <p className="text-secondary">{p.description || "No description provided."}</p>
                  </div>
                  <div className="card-footer">
                    <div className="d-flex">
                      <button 
                        className={`btn ${currentProjectId === p.id ? 'btn-primary' : 'btn-outline-primary'}`}
                        onClick={() => setCurrentProjectId(p.id)}
                      >
                        {currentProjectId === p.id ? 'Active' : 'Select Project'}
                      </button>
                      <div className="ms-auto btn-list">
                        <button className="btn btn-icon btn-white" title="Project Settings">
                          <IconSettings size={18} />
                        </button>
                        <button className="btn btn-icon btn-white" title="Project Members">
                          <IconUsers size={18} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {projects.length === 0 && (
              <div className="col-12 text-center py-5">
                <div className="empty">
                  <div className="empty-icon">
                    <IconFolder size={48} />
                  </div>
                  <p className="empty-title">No projects found</p>
                  <p className="empty-subtitle text-muted">
                    You are not a member of any projects yet.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="modal modal-blur fade show" style={{ display: 'block' }} tabIndex={-1}>
          <div className="modal-dialog modal-lg modal-dialog-centered" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">New project</h5>
                <button type="button" className="btn-close" onClick={() => setShowCreateModal(false)} aria-label="Close"></button>
              </div>
              <form onSubmit={handleCreateProject}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Project Name</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder="My awesome project"
                      required
                      value={newProject.name}
                      onChange={(e) => setNewProject({...newProject, name: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Description</label>
                    <textarea 
                      className="form-control" 
                      rows={3}
                      placeholder="What is this project about?"
                      value={newProject.description}
                      onChange={(e) => setNewProject({...newProject, description: e.target.value})}
                    ></textarea>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-link link-secondary" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary ms-auto">
                    <IconPlus size={18} />
                    Create project
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {showCreateModal && <div className="modal-backdrop fade show"></div>}
    </div>
  );
}
