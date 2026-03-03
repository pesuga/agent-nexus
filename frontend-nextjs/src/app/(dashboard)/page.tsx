"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "@/context/AppContext";

export default function DashboardRoot() {
  const router = useRouter();
  const { currentProjectId } = useAppContext();

  useEffect(() => {
    // If we have a selected project, go to its overview, otherwise go to projects list
    if (currentProjectId) {
      router.push(`/projects/${currentProjectId}/overview`);
    } else {
      router.push("/projects");
    }
  }, [currentProjectId, router]);

  return (
    <div className="d-flex align-items-center justify-content-center" style={{ height: '50vh' }}>
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  );
}
