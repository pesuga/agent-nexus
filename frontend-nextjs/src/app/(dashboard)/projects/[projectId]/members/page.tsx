"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";
import { Project, User } from "@/types/dispatch";
import { useParams } from "next/navigation";
import { IconPlus, IconUser, IconTrash, IconChevronLeft } from "@tabler/icons-react";
import Link from "next/link";

interface ProjectMembership {
  project_id: string;
  user_id: string;
  role: string;
  created_at: string;
}

export default function ProjectMembersPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  
  const [members, setMembers] = useState<ProjectMembership[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [showAddModal, setShowCreateModal] = useState(false);
  
  const [newMember, setNewMember] = useState({
    user_id: "",
    role: "member"
  });

  const { config, user: currentUser, projects } = useAppContext();

  const fetchData = useCallback(async () => {
    try {
      const headers = {
        'X-Actor-Role': currentUser?.actor_role || '',
        'X-Actor-Id': currentUser?.actor_id || '',
        'X-API-Token': config.apiToken,
      };

      const [membersResp, usersResp] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/projects/${projectId}/members`, { headers }),
        fetch(`${config.apiBaseUrl}/api/users`, { headers })
      ]);

      if (membersResp.ok) {
        setMembers(await membersResp.json());
      }
      if (usersResp.ok) {
        setAvailableUsers(await usersResp.json());
      }
      
      const foundProject = projects.find(p => p.id === projectId);
      if (foundProject) setProject(foundProject);

    } catch (err) {
      console.error("Failed to fetch project member data", err);
    } finally {
      setLoading(false);
    }
  }, [config, currentUser, projectId, projects]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/projects/${projectId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': currentUser?.actor_role || '',
          'X-Actor-Id': currentUser?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify(newMember)
      });
      if (resp.ok) {
        setShowCreateModal(false);
        setNewMember({ user_id: "", role: "member" });
        fetchData();
      } else {
        const data = await resp.json();
        alert(data.detail || "Failed to add member");
      }
    } catch (err) {
      console.error("Failed to add member", err);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!confirm("Are you sure you want to remove this member?")) return;
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/projects/${projectId}/members/${userId}`, {
        method: 'DELETE',
        headers: {
          'X-Actor-Role': currentUser?.actor_role || '',
          'X-Actor-Id': currentUser?.actor_id || '',
          'X-API-Token': config.apiToken,
        }
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (err) {
      console.error("Failed to remove member", err);
    }
  };

  if (loading) return <div>Loading members...</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header d-print-none">
        <div className="container-xl">
          <div className="row g-2 align-items-center">
            <div className="col">
              <div className="mb-1">
                <Link href="/projects" className="btn btn-link link-secondary p-0">
                  <IconChevronLeft size={16} />
                  Back to projects
                </Link>
              </div>
              <h2 className="page-title">
                Members: {project?.name || projectId}
              </h2>
            </div>
            {currentUser?.actor_role === 'human_admin' && (
              <div className="col-auto ms-auto d-print-none">
                <div className="btn-list">
                  <button 
                    className="btn btn-primary d-none d-sm-inline-block"
                    onClick={() => setShowCreateModal(true)}
                  >
                    <IconPlus size={18} />
                    Add member
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="container-xl">
          <div className="card">
            <div className="table-responsive">
              <table className="table table-vcenter card-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Joined</th>
                    <th className="w-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => {
                    const user = availableUsers.find(u => u.id === m.user_id);
                    return (
                      <tr key={m.user_id}>
                        <td>
                          <div className="d-flex py-1 align-items-center">
                            <span className="avatar me-2">{user?.display_name?.charAt(0) || user?.email?.charAt(0) || "?"}</span>
                            <div className="flex-fill">
                              <div className="font-weight-medium">{user?.display_name || "N/A"}</div>
                              <div className="text-secondary small">{user?.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="text-secondary">
                          <span className="badge bg-blue-lt text-uppercase">{m.role}</span>
                        </td>
                        <td className="text-secondary small">
                          {new Date(m.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          {currentUser?.actor_role === 'human_admin' && m.user_id !== currentUser.actor_id && (
                            <button 
                              className="btn btn-icon btn-white text-danger"
                              onClick={() => handleRemoveMember(m.user_id)}
                              title="Remove member"
                            >
                              <IconTrash size={18} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Add Member Modal */}
      {showAddModal && (
        <div className="modal modal-blur fade show" style={{ display: 'block' }} tabIndex={-1}>
          <div className="modal-dialog modal-dialog-centered" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Add member to project</h5>
                <button type="button" className="btn-close" onClick={() => setShowCreateModal(false)} aria-label="Close"></button>
              </div>
              <form onSubmit={handleAddMember}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Select User</label>
                    <select 
                      className="form-select"
                      required
                      value={newMember.user_id}
                      onChange={(e) => setNewMember({...newMember, user_id: e.target.value})}
                    >
                      <option value="">Choose a user...</option>
                      {availableUsers
                        .filter(u => !members.some(m => m.user_id === u.id))
                        .map(u => (
                          <option key={u.id} value={u.id}>{u.display_name} ({u.email})</option>
                        ))
                      }
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Role</label>
                    <select 
                      className="form-select"
                      value={newMember.role}
                      onChange={(e) => setNewMember({...newMember, role: e.target.value})}
                    >
                      <option value="member">Member</option>
                      <option value="owner">Owner</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-link link-secondary" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary ms-auto">
                    <IconPlus size={18} />
                    Add member
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {showAddModal && <div className="modal-backdrop fade show"></div>}
    </div>
  );
}
