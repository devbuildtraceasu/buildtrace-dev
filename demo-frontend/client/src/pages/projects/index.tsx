import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

type Project = {
  id: string;
  name: string;
  description?: string;
  updatedAt?: string;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    // Placeholder: load from server when API exists
    const seed: Project[] = [];
    if (active) {
      setProjects(seed);
      setLoading(false);
    }
    return () => { active = false; };
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-card p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-900">Projects</h1>
          <Button size="sm" disabled>
            New Project
          </Button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-6">
        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : projects.length === 0 ? (
          <div className="text-gray-500">No projects yet.</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {projects.map((p) => (
              <li key={p.id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">{p.name}</div>
                  {p.description && <div className="text-sm text-gray-600">{p.description}</div>}
                </div>
                <Button asChild variant="link" size="sm" className="p-0">
                  <Link to="#">Open</Link>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}


