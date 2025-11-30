import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import AppLayout from "@/components/layout/AppLayout";
import HomePage from "@/pages/home";
import ComparisonPage from "@/pages/comparison";
import NotFound from "@/pages/not-found";
import ProjectsPage from "@/pages/projects";
import Landing from "@/pages/Landing";

export default function Router() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <BrowserRouter>
      {isLoading || !isAuthenticated ? (
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="*" element={<Landing />} />
        </Routes>
      ) : (
        <AppLayout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/compare/:id" element={<ComparisonPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AppLayout>
      )}
    </BrowserRouter>
  );
}
