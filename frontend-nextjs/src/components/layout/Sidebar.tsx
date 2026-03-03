"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { 
  IconLayoutKanban, 
  IconUsers, 
  IconSettings, 
  IconLayoutDashboard,
  IconFolders,
  IconShieldLock,
  IconDatabase
} from "@tabler/icons-react";
import { useAppContext } from "@/context/AppContext";

export default function Sidebar() {
  const pathname = usePathname();
  const params = useParams();
  const { user, currentProjectId } = useAppContext();

  // Use projectId from URL params if available, otherwise fallback to context
  const activeProjectId = (params.projectId as string) || currentProjectId;

  const navItems = [
    { label: "Overview", href: `/projects/${activeProjectId}/overview`, icon: <IconLayoutDashboard size={20} /> },
    { label: "Kanban", href: `/projects/${activeProjectId}/tasks`, icon: <IconLayoutKanban size={20} /> },
    { label: "Projects", href: "/projects", icon: <IconFolders size={20} /> },
    { label: "Agents", href: `/projects/${activeProjectId}/agents`, icon: <IconUsers size={20} /> },
    { label: "Settings", href: "/settings", icon: <IconSettings size={20} /> },
  ];

  const adminItems = [
    { label: "User Management", href: "/admin/users", icon: <IconShieldLock size={20} /> },
    { label: "Model Registry", href: "/admin/models", icon: <IconDatabase size={20} /> },
  ];

  return (
    <aside className="navbar navbar-vertical navbar-expand-lg" data-bs-theme="dark">
      <div className="container-fluid">
        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#sidebar-menu">
          <span className="navbar-toggler-icon"></span>
        </button>
        <h1 className="navbar-brand navbar-brand-autodark">
          <Link href="/">
            <span className="navbar-brand-image">
              <IconLayoutDashboard className="text-primary me-2" />
              Agent Nexus
            </span>
          </Link>
        </h1>
        <div className="collapse navbar-collapse" id="sidebar-menu">
          <ul className="navbar-nav pt-lg-3">
            {navItems.map((item) => (
              <li key={item.href} className={`nav-item ${pathname === item.href ? "active" : ""}`}>
                <Link className="nav-link" href={item.href}>
                  <span className="nav-link-icon d-md-none d-lg-inline-block">
                    {item.icon}
                  </span>
                  <span className="nav-link-title">
                    {item.label}
                  </span>
                </Link>
              </li>
            ))}

            {user?.actor_role === 'human_admin' && (
              <>
                <div className="hr-text text-muted small mt-4 mb-2">Administration</div>
                {adminItems.map((item) => (
                  <li key={item.href} className={`nav-item ${pathname === item.href ? "active" : ""}`}>
                    <Link className="nav-link" href={item.href}>
                      <span className="nav-link-icon d-md-none d-lg-inline-block">
                        {item.icon}
                      </span>
                      <span className="nav-link-title">
                        {item.label}
                      </span>
                    </Link>
                  </li>
                ))}
              </>
            )}
          </ul>
        </div>
      </div>
    </aside>
  );
}
