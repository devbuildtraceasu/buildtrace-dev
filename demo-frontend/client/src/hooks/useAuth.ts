import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export function useAuth() {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      if (!isMounted) return;
      setUser(data.session?.user ?? null);
      setIsLoading(false);
    };
    init();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      isMounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
  };
}