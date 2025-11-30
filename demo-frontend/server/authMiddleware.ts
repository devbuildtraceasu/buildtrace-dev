import type { RequestHandler } from "express";
import { supabaseServer } from "./supabaseClient";

export interface AuthContext {
  userId: string;
  email?: string | null;
}

declare module "express-serve-static-core" {
  interface Request {
    auth?: AuthContext;
  }
}

export const requireAuth: RequestHandler = async (req, res, next) => {
  try {
    const authHeader = req.headers["authorization"] || req.headers["Authorization"];
    if (!authHeader || Array.isArray(authHeader)) {
      return res.status(401).json({ message: "Unauthorized" });
    }

    const [scheme, token] = authHeader.split(" ");
    if (scheme?.toLowerCase() !== "bearer" || !token) {
      return res.status(401).json({ message: "Unauthorized" });
    }

    const { data, error } = await supabaseServer.auth.getUser(token);
    if (error || !data?.user) {
      return res.status(401).json({ message: "Unauthorized" });
    }

    req.auth = {
      userId: data.user.id,
      email: data.user.email,
    };
    return next();
  } catch (_err) {
    return res.status(401).json({ message: "Unauthorized" });
  }
};


