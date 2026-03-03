"use client";

import { useAppContext } from "@/context/AppContext";
import { IconBell, IconSearch } from "@tabler/icons-react";

export default function Header() {
  const { projects, currentProjectId, setCurrentProjectId, user, logout } = useAppContext();

  return (
    <header className="navbar navbar-expand-md d-none d-lg-flex d-print-none">
      <div className="container-xl">
        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbar-menu">
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className="navbar-nav flex-row order-md-last">
          <div className="nav-item d-none d-md-flex me-3">
            <div className="btn-list">
              <a href="#" className="nav-link px-0" title="Show notifications" data-bs-toggle="dropdown" data-bs-auto-close="outside" role="button" aria-expanded="false">
                <IconBell size={20} />
                <span className="badge bg-red"></span>
              </a>
            </div>
          </div>
          <div className="nav-item dropdown">
            <a href="#" className="nav-link d-flex lh-1 text-reset p-0" data-bs-toggle="dropdown" aria-label="Open user menu">
              <span
                className="avatar avatar-sm"
                style={user?.avatar_url ? { backgroundImage: `url(${user.avatar_url})` } : undefined}
              >
                {!user?.avatar_url && (user?.display_name?.charAt(0) || user?.email?.charAt(0) || "?")}
              </span>
              <div className="d-none d-xl-block ps-2">
                <div>{user?.display_name || user?.email || "Guest"}</div>
                <div className="mt-1 small text-secondary">{user?.actor_role || "User"}</div>
              </div>
            </a>
            <div className="dropdown-menu dropdown-menu-end dropdown-menu-arrow">
              <a href="/profile" className="dropdown-item">Profile</a>
              <div className="dropdown-divider"></div>
              <a href="/settings" className="dropdown-item">Settings</a>
              <button onClick={logout} className="dropdown-item">Logout</button>
            </div>
          </div>
        </div>
        <div className="collapse navbar-collapse" id="navbar-menu">
          <div className="d-flex flex-column flex-md-row flex-fill align-items-stretch align-items-md-center">
            <div className="me-md-3">
              <select 
                className="form-select"
                value={currentProjectId}
                onChange={(e) => setCurrentProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="input-icon">
              <span className="input-icon-addon">
                <IconSearch size={18} />
              </span>
              <input type="text" className="form-control" placeholder="Search tasks..." aria-label="Search tasks" />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
