import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ViewMode } from "@/features/comparison/models";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";

const VIEW_MODES: { value: ViewMode; label: string }[] = [
  { value: "side-by-side", label: "Side by Side" },
  { value: "overlay", label: "Overlay" },
  { value: "baseline", label: "Baseline Only" },
  { value: "revised", label: "Revised Only" },
];

export default function ViewModeToggle() {
  const { viewMode, setViewMode } = useComparisonStore();

  return (
    <div className="flex items-center space-x-2" data-testid="view-mode-toggle">
      {VIEW_MODES.map(({ value, label }) => {
        const isActive = viewMode === value;
        
        return (
          <Button
            key={value}
            onClick={() => setViewMode(value)}
            variant={isActive ? "default" : "outline"}
            size="sm"
            className={cn(
              "transition-colors",
              isActive && "view-mode-active"
            )}
            data-testid={`button-view-mode-${value}`}
          >
            {label}
          </Button>
        );
      })}
    </div>
  );
}
