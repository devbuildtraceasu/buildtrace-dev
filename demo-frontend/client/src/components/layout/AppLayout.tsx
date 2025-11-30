import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Bell, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabaseClient";
import { type User } from "@shared/schema";
import logoPath from "@assets/BuildTrace_Logo_1757990973624.webp";

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation();
  const { user } = useAuth();
  
  // Type the user properly
  const typedUser = user as User | undefined;

  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen">
      {/* Navigation Header */}
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <Link to="/" className="flex items-center" data-testid="logo-link">
                <img 
                  src={logoPath} 
                  alt="BuildTrace AI" 
                  className="h-10 w-auto" 
                />
              </Link>
              <div className="hidden md:flex items-center space-x-6 h-16">
                <Link
                  to="/"
                  className={`h-16 flex items-center border-b-2 ${
                    location.pathname === "/"
                      ? "text-gray-900 font-medium border-primary"
                      : "text-gray-500 hover:text-gray-900 border-transparent"
                  }`}
                  data-testid="nav-home"
                >
                  Home
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" data-testid="button-notifications">
                <Bell className="h-4 w-4 text-gray-400" />
              </Button>
              
              {typedUser && (
                <div className="flex items-center space-x-3">
                  <div className="text-sm">
                    <div className="font-medium text-gray-900" data-testid="text-user-name">
                      {typedUser.firstName && typedUser.lastName ? `${typedUser.firstName} ${typedUser.lastName}` : 'User'}
                    </div>
                    <div className="text-gray-500" data-testid="text-user-email">
                      {typedUser.email}
                    </div>
                  </div>
                  
                  {typedUser.profileImageUrl ? (
                    <img 
                      src={typedUser.profileImageUrl} 
                      alt="Profile" 
                      className="w-8 h-8 rounded-full object-cover" 
                      data-testid="img-user-avatar"
                    />
                  ) : (
                    <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center" data-testid="avatar-user-default">
                      <span className="text-xs text-gray-600 font-medium">
                        {typedUser.firstName?.[0] || typedUser.email?.[0] || 'U'}
                      </span>
                    </div>
                  )}
                  
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleLogout}
                    data-testid="button-logout"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
