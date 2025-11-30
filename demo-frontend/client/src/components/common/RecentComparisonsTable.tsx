import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Search, Trash2, Eye } from "lucide-react";
import { useRecentStore } from "@/features/recent/state/useRecentStore";
import { recentService } from "@/features/recent/services/recentService";
import { RecentItem } from "@/features/recent/models";

export default function RecentComparisonsTable() {
  const {
    items,
    query,
    loading,
    setItems,
    setQuery,
    removeItem,
    setLoading,
    getFilteredItems,
  } = useRecentStore();

  const [deleteId, setDeleteId] = useState<string | null>(null);
  
  const filteredItems = getFilteredItems();

  const fileBaseName = (name: string) => {
    if (!name) return name;
    const parts = name.split("/");
    return parts[parts.length - 1];
  };

  useEffect(() => {
    const loadItems = async () => {
      setLoading(true);
      try {
        const loadedItems = await recentService.load();
        setItems(loadedItems);
      } catch (error) {
        console.error("Failed to load recent items:", error);
      } finally {
        setLoading(false);
      }
    };

    loadItems();
  }, [setItems, setLoading]);

  const handleDelete = async (id: string) => {
    try {
      await recentService.remove(id);
      removeItem(id);
      setDeleteId(null);
    } catch (error) {
      console.error("Failed to delete item:", error);
    }
  };

  const getBadgeColor = (drawingNumber: string) => {
    const colors = ["blue", "green", "purple", "orange", "pink"];
    const index = drawingNumber.charCodeAt(0) % colors.length;
    return colors[index];
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-8">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-2xl shadow-card p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-900" data-testid="recent-comparisons-title">
            Recent Comparisons
          </h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              type="text"
              placeholder="Search comparisons..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-10 w-64"
              data-testid="input-search-comparisons"
            />
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="table-recent-comparisons">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Date</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Drawing Number</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Baseline</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Revised</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Changes</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    {query ? "No comparisons match your search." : "No recent comparisons found."}
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr 
                    key={item.id} 
                    className="hover:bg-gray-50"
                    data-testid={`row-comparison-${item.id}`}
                  >
                    <td className="py-4 px-4 text-sm text-gray-600" data-testid="text-date">
                      {new Date(item.date).toLocaleDateString()}
                    </td>
                    <td className="py-4 px-4" data-testid="badge-drawing-number">
                      {item.drawingNumber && (
                        <Badge variant="secondary" className={`bg-${getBadgeColor(item.drawingNumber)}-100 text-${getBadgeColor(item.drawingNumber)}-800`}>
                          {item.drawingNumber}
                        </Badge>
                      )}
                    </td>
                    <td className="py-4 px-4 text-sm text-gray-600" data-testid="text-baseline">
                      {fileBaseName(item.baselineName)}
                    </td>
                    <td className="py-4 px-4 text-sm text-gray-600" data-testid="text-revised">
                      {fileBaseName(item.revisedName)}
                    </td>
                    <td className="py-4 px-4 text-sm text-gray-600" data-testid="text-changes">
                      {item.changesCount} changes
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="link"
                          size="sm"
                          asChild
                          className="text-primary hover:text-blue-700 p-0"
                          data-testid={`button-view-${item.id}`}
                        >
                          <Link to={`/compare/${item.id}`}>
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteId(item.id)}
                          className="text-red-600 hover:text-red-700 p-1"
                          data-testid={`button-delete-${item.id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Comparison</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this comparison? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="button-cancel-delete">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && handleDelete(deleteId)}
              className="bg-red-600 hover:bg-red-700"
              data-testid="button-confirm-delete"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
