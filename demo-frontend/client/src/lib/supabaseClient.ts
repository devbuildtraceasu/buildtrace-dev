import { createClient } from "@supabase/supabase-js";

const envUrl = (import.meta as any).env?.VITE_SUPABASE_URL as string | undefined;
const envKey = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY as string | undefined;
const globalUrl = (globalThis as any).SUPABASE_URL as string | undefined;
const globalKey = (globalThis as any).SUPABASE_ANON_KEY as string | undefined;

const supabaseUrl = envUrl || globalUrl;
const supabaseAnonKey = envKey || globalKey;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing VITE_SUPABASE_URL/VITE_SUPABASE_ANON_KEY (or global overrides) for Supabase");
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);


