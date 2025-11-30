import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Settings } from "lucide-react";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";

export default function ComparisonToolbar() {
  const { zoom, setZoom } = useComparisonStore();

  const handleZoomChange = (value: string) => {
    setZoom(parseInt(value));
  };

  return (
    <div className="flex items-center flex-wrap gap-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
        <Input
          type="text"
          placeholder="Search drawing number"
          className="pl-10 h-9 w-auto min-w-[14rem]"
          data-testid="input-search-drawing"
        />
      </div>

      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-600">Zoom:</span>
        <Select value={zoom.toString()} onValueChange={handleZoomChange}>
          <SelectTrigger className="w-20 h-9" data-testid="select-zoom">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="50">50%</SelectItem>
            <SelectItem value="75">75%</SelectItem>
            <SelectItem value="100">100%</SelectItem>
            <SelectItem value="150">150%</SelectItem>
            <SelectItem value="200">200%</SelectItem>
            <SelectItem value="300">300%</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button variant="outline" size="sm" data-testid="button-view-settings">
        <Settings className="h-4 w-4" />
      </Button>
    </div>
  );
}
