import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import Stepper from "@/components/common/Stepper";
import UploadDropzoneWithAuth from "@/components/common/UploadDropzoneWithAuth";
import RecentComparisonsTable from "@/components/common/RecentComparisonsTable";
import { type UploadedFile, type InsertComparison } from "@shared/schema";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";
import { apiRequest } from "@/lib/queryClient";
import { recentService } from "@/features/recent/services/recentService";

export default function HomePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { loading, setLoading, setInput, setResult, setError } = useComparisonStore();
  
  const [baselineFile, setBaselineFile] = useState<UploadedFile | null>(null);
  const [revisedFile, setRevisedFile] = useState<UploadedFile | null>(null);
  
  const currentStep = baselineFile && revisedFile ? 3 : baselineFile ? 2 : 1;
  const canCompare = baselineFile && revisedFile && !loading;

  const handleCompare = async () => {
    if (!baselineFile || !revisedFile) return;
    
    setLoading(true);
    setError(undefined);

    try {
      // Fire-and-forget the long-running compare request
      apiRequest('POST', '/api/compare/pdf', {
        baselineFileId: baselineFile.id,
        revisedFileId: revisedFile.id,
        baselineOriginalName: baselineFile.originalName,
        revisedOriginalName: revisedFile.originalName,
        uploadOutputs: true,
      }).catch(() => {
        // Best-effort; failure will be surfaced by polling view
      });

      // Seed input so the comparison page can render viewers & poll
      setInput({
        baseline: {
          id: baselineFile.id,
          name: baselineFile.originalName || 'Baseline',
          size: baselineFile.fileSize,
          type: 'pdf',
          url: `/api/files/${baselineFile.id}/download`,
        },
        revised: {
          id: revisedFile.id,
          name: revisedFile.originalName || 'Revised',
          size: revisedFile.fileSize,
          type: 'pdf',
          url: `/api/files/${revisedFile.id}/download`,
        },
      });

      toast({
        title: "Processing started",
        description: "We’ll load results when they’re ready. This can take a few minutes.",
      });

      // Poll for the newly created comparison id and navigate when found
      let cancelled = false;
      const poll = async () => {
        if (cancelled) return;
        try {
          const res = await apiRequest('GET', '/api/comparisons');
          const list = await res.json();
          const match = Array.isArray(list)
            ? list.find((c: any) => c?.baselineFileId === baselineFile.id && c?.revisedFileId === revisedFile.id)
            : undefined;
          if (match?.id) {
            navigate(`/compare/${match.id}`);
            setLoading(false);
            return;
          }
        } catch (_) {
          // ignore and continue
        }
        setTimeout(poll, 3000);
      };
      poll();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start comparison";
      setError(message);
      
      toast({
        title: "Comparison failed",
        description: message,
        variant: "destructive",
      });
      setLoading(false);
    } finally {
      // loading state is cleared on successful navigation above
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12" data-testid="hero-section">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">BuildTrace AI</h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Intelligently detect and analyze changes between construction drawing versions
        </p>
      </div>

      {/* Drawing Comparison Card */}
      <div className="bg-white rounded-2xl shadow-card p-8" data-testid="drawing-comparison-card">
        <h2 className="text-2xl font-semibold text-gray-900 mb-8">Drawing Comparison</h2>
        
        {/* Stepper */}
        <Stepper
          currentStep={currentStep}
          steps={["Upload Old", "Upload New", "Process", "Results"]}
          className="mb-8"
        />

        {/* Upload Dropzones */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          <UploadDropzoneWithAuth
            label="Baseline Drawing (Old)"
            uploadedFile={baselineFile}
            onFileUploaded={setBaselineFile}
          />
          <UploadDropzoneWithAuth
            label="Revised Drawing (New)"
            uploadedFile={revisedFile}
            onFileUploaded={setRevisedFile}
          />
        </div>

        {/* Compare Button */}
        <div className="text-center">
          <Button
            onClick={handleCompare}
            disabled={!canCompare}
            size="lg"
            className="px-8 py-3 text-lg font-semibold"
            data-testid="button-compare-drawings"
          >
            {loading ? "Processing..." : "Compare Drawings"}
          </Button>
        </div>
      </div>

      {/* Recent Comparisons Table */}
      <RecentComparisonsTable />
    </div>
  );
}
