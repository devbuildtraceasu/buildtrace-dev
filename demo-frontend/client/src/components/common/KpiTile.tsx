import { cn } from "@/lib/utils";

interface KpiTileProps {
  value?: number;
  label: string;
  variant: "added" | "modified" | "removed";
  className?: string;
}

export default function KpiTile({ value, label, variant, className }: KpiTileProps) {
  const variantStyles = {
    added: "bg-green-50 border-green-200 text-green-600",
    modified: "bg-amber-50 border-amber-200 text-amber-600", 
    removed: "bg-red-50 border-red-200 text-red-600",
  };

  const labelStyles = {
    added: "text-green-700",
    modified: "text-amber-700",
    removed: "text-red-700",
  };

  return (
    <div 
      className={cn(
        "border rounded-xl p-4 text-center",
        variantStyles[variant],
        className
      )}
      data-testid={`kpi-tile-${variant}`}
    >
      <div className={cn("text-3xl font-bold mb-1", variantStyles[variant])}>
        {typeof value === 'number' ? value : '-'}
      </div>
      <div className={cn("text-sm font-medium", labelStyles[variant])}>
        {label}
      </div>
    </div>
  );
}
