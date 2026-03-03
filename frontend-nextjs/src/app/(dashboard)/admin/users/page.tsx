"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";
import { User } from "@/types/dispatch";
import { IconPlus, IconUser, IconUserOff, IconEdit, IconX } from "@tabler/icons-react";

export default function UsersAdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // New user form state
  const [newUser, setNewUser] = useState({
    email: "",
    password: "",
    display_name: "",
    global_role: "member"
  });

  const { config, user: currentUser } = useAppContext();

  const fetchUsers = useCallback(async () => {
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/users`, {
        headers: {
          'X-Actor-Role': currentUser?.actor_role || '',
          'X-Actor-Id': currentUser?.actor_id || '',
          'X-API-Token': config.apiToken,
        }
      });
      if (resp.ok) {
        const data = await resp.json();
        setUsers(data);
      } else {
        const data = await resp.json();
        setError(data.detail || "Failed to fetch users");
      }
    } catch (err) {
      setError("An error occurred while fetching users");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [config, currentUser]);

  useEffect(() => {
    if (currentUser?.actor_role === 'human_admin') {
      fetchUsers();
    } else {
      setError("You do not have permission to view this page");
      setLoading(false);
    }
  }, [currentUser, fetchUsers]);

  const toggleUserStatus = async (user: User) => {
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/users/${user.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': currentUser?.actor_role || '',
          'X-Actor-Id': currentUser?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify({ disabled: !user.disabled })
      });
      if (resp.ok) {
        fetchUsers();
      }
    } catch (err) {
      console.error("Failed to toggle user status", err);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': currentUser?.actor_role || '',
          'X-Actor-Id': currentUser?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify(newUser)
      });
      if (resp.ok) {
        setShowCreateModal(false);
        setNewUser({ email: "", password: "", display_name: "", global_role: "member" });
        fetchUsers();
      } else {
        const data = await resp.json();
        alert(data.detail || "Failed to create user");
      }
    } catch (err) {
      console.error("Failed to create user", err);
    }
  };

  if (loading) return <div>Loading users...</div>;
  if (error) return <div className="alert alert-danger">{error}</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header d-print-none">
        <div className="container-xl">
          <div className="row g-2 align-items-center">
            <div className="col">
              <h2 className="page-title">
                User Management
              </h2>
            </div>
            <div className="col-auto ms-auto d-print-none">
              <div className="btn-list">
                <button 
                  className="btn btn-primary d-none d-sm-inline-block"
                  onClick={() => setShowCreateModal(true)}
                >
                  <IconPlus size={18} />
                  Create new user
                </button>
              </div>
            </div>
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
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th className="w-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.display_name || "N/A"}</td>
                      <td className="text-secondary">{u.email}</td>
                      <td className="text-secondary">{u.global_role}</td>
                      <td>
                        {u.disabled ? (
                          <span className="badge bg-red-lt">Disabled</span>
                        ) : (
                          <span className="badge bg-green-lt">Active</span>
                        )}
                      </td>
                      <td>
                        <div className="btn-list flex-nowrap">
                          <button className="btn btn-white btn-sm">
                            <IconEdit size={16} />
                            Edit
                          </button>
                          <button 
                            className={`btn btn-sm ${u.disabled ? 'btn-success' : 'btn-danger'}`}
                            onClick={() => toggleUserStatus(u)}
                          >
                            {u.disabled ? <IconUser size={16} /> : <IconUserOff size={16} />}
                            {u.disabled ? 'Enable' : 'Disable'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="modal modal-blur fade show" style={{ display: 'block' }} tabIndex={-1}>
          <div className="modal-dialog modal-lg modal-dialog-centered" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">New user</h5>
                <button type="button" className="btn-close" onClick={() => setShowCreateModal(false)} aria-label="Close"></button>
              </div>
              <form onSubmit={handleCreateUser}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Display Name</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder="User's name"
                      value={newUser.display_name}
                      onChange={(e) => setNewUser({...newUser, display_name: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Email address</label>
                    <input 
                      type="email" 
                      className="form-control" 
                      placeholder="user@example.com"
                      required
                      value={newUser.email}
                      onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Password</label>
                    <input 
                      type="password" 
                      className="form-control" 
                      placeholder="Password"
                      required
                      value={newUser.password}
                      onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Global Role</label>
                    <select 
                      className="form-select"
                      value={newUser.global_role}
                      onChange={(e) => setNewUser({...newUser, global_role: e.target.value})}
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-link link-secondary" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary ms-auto">
                    <IconPlus size={18} />
                    Create user
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
