"use client";

import KanbanBoard from "@/components/kanban/KanbanBoard";
import { useParams } from "next/navigation";

export default function ProjectTasksPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <main>
      <KanbanBoard projectId={projectId} />
    </main>
  );
}
