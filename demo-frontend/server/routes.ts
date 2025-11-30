import type { Express } from "express";
import express from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertComparisonSchema, insertUploadedFileSchema } from "@shared/schema";
import { requireAuth } from "./authMiddleware";
import { z } from "zod";
import multer from "multer";
import { supabaseServer } from "./supabaseClient";
import { nanoid } from "nanoid";

// Configure multer for file uploads (memory storage for pushing to Supabase Storage)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  },
  fileFilter: (_req: any, file: any, cb: any) => {
    const allowedTypes = [
      'application/pdf',
      'image/png', 
      'image/jpeg',
      'application/dwg',
      'application/dxf'
    ];
    if (allowedTypes.includes(file.mimetype) || 
        file.originalname.toLowerCase().endsWith('.dwg') ||
        file.originalname.toLowerCase().endsWith('.dxf')) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  }
});

export async function registerRoutes(app: Express): Promise<Server> {
  // No server-side session auth; we validate Supabase JWT per-request

  // Ensure the storage bucket exists (idempotent)
  try {
    const { data: buckets } = await supabaseServer.storage.listBuckets();
    const hasBucket = (buckets || []).some((b) => b.name === "drawings");
    if (!hasBucket) {
      await supabaseServer.storage.createBucket("drawings", { public: false });
    }
  } catch (e) {
    // Non-fatal; upload endpoint will surface errors if bucket truly missing
    console.warn("Warning: could not verify/create 'drawings' bucket", e);
  }

  // Auth routes
  app.get('/api/auth/user', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      // Upsert minimal user record to keep DB consistent
      const user = await storage.upsertUser({
        id: userId,
        email: req.auth?.email ?? undefined,
        firstName: undefined,
        lastName: undefined,
        profileImageUrl: undefined,
      });
      res.json(user);
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });

  // File upload endpoints
  app.post('/api/files/upload', requireAuth, upload.single('file'), async (req: any, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ message: 'No file uploaded' });
      }

      const userId = req.auth!.userId;
      // Ensure user exists for FK
      await storage.upsertUser({
        id: userId,
        email: req.auth?.email ?? undefined,
        firstName: undefined,
        lastName: undefined,
        profileImageUrl: undefined,
      });

      // Sanitize filename to remove invalid characters
      const sanitizedFilename = req.file.originalname
        .replace(/[^\x00-\x7F]/g, '_') // Replace non-ASCII characters
        .replace(/[<>:"/\\|?*]/g, '_') // Replace invalid filename characters
        .replace(/\s+/g, '_'); // Replace spaces with underscores

      // Upload to Supabase Storage (bucket: drawings)
      const objectPath = `${userId}/${Date.now()}_${sanitizedFilename}`;
      const { error: uploadError } = await supabaseServer.storage
        .from('drawings')
        .upload(objectPath, req.file.buffer, {
          contentType: req.file.mimetype,
          upsert: false,
        });

      if (uploadError) {
        throw uploadError;
      }

      const fileData = insertUploadedFileSchema.parse({
        userId,
        fileName: objectPath, // store storage object path
        originalName: req.file.originalname,
        mimeType: req.file.mimetype,
        fileSize: req.file.size,
        fileUrl: `/api/files/${objectPath}/download`,
      });

      const uploadedFile = await storage.createUploadedFile(fileData);
      res.json(uploadedFile);
    } catch (error) {
      console.error('File upload error:', error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid file data", errors: error.errors });
      }
      const msg = (error as any)?.message || 'Failed to upload file';
      res.status(500).json({ message: 'Failed to upload file', error: msg });
    }
  });

  app.get('/api/files', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const files = await storage.getUserUploadedFiles(userId);
      res.json(files);
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch files' });
    }
  });

  app.delete('/api/files/:id', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const file = await storage.getUploadedFile(req.params.id);
      
      if (!file || file.userId !== userId) {
        return res.status(404).json({ message: 'File not found' });
      }

      // Delete object from Supabase Storage
      await supabaseServer.storage.from('drawings').remove([file.fileName]);

      const success = await storage.deleteUploadedFile(req.params.id);
      if (!success) {
        return res.status(404).json({ message: 'File not found' });
      }
      
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ message: 'Failed to delete file' });
    }
  });

  // Protected file download endpoint
  app.get('/api/files/:id/download', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      // Support both id-based and path-based param for backward compatibility
      const param = req.params.id;
      let file = await storage.getUploadedFile(param);
      if (!file) {
        // treat param as object path if record not found
        // find by fileName
        const userFiles = await storage.getUserUploadedFiles(userId);
        file = userFiles.find(f => f.fileName === param);
      }

      if (!file || file.userId !== userId) {
        return res.status(404).json({ message: 'File not found' });
      }

      // Create a short-lived signed URL and redirect
      const { data, error } = await supabaseServer.storage
        .from('drawings')
        .createSignedUrl(file.fileName, 60, { download: file.originalName });
      if (error || !data?.signedUrl) {
        return res.status(500).json({ message: 'Failed to create download URL' });
      }
      res.redirect(data.signedUrl);
    } catch (error) {
      res.status(500).json({ message: 'Failed to serve file' });
    }
  });
  
  // Proxy compare to external service (synchronous)
  app.post('/api/compare/pdf', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });

      const { baselineFileId, revisedFileId, dpi, debug, drawingNumber, baselineOriginalName, revisedOriginalName, uploadOutputs = true } = req.body || {};
      if (!baselineFileId || !revisedFileId) {
        return res.status(400).json({ message: 'baselineFileId and revisedFileId are required' });
      }

      const baselineFile = await storage.getUploadedFile(baselineFileId);
      const revisedFile = await storage.getUploadedFile(revisedFileId);
      if (!baselineFile || !revisedFile || baselineFile.userId !== userId || revisedFile.userId !== userId) {
        return res.status(400).json({ message: 'Invalid file references' });
      }

      // Create comparison row first for durability
      const comparisonRow = await storage.createComparison({
        userId,
        baselineFileId,
        revisedFileId,
        baselineOriginalName: baselineOriginalName || baselineFile?.originalName,
        revisedOriginalName: revisedOriginalName || revisedFile?.originalName,
        drawingNumber,
        autoDetectedDrawingNumber: false,
        status: 'processing',
        kpis: null as any,
        byCategory: null as any,
        changes: null as any,
      } as any);

      const comparisonId = comparisonRow.id;

      const outputPrefix = `overlays/${userId}/${comparisonId}`;

      const payload: any = {
        supabase: {
          url: process.env.SUPABASE_URL,
          key: process.env.SUPABASE_SERVICE_ROLE_KEY,
        },
        old_pdf: { bucket: 'drawings', path: baselineFile.fileName },
        new_pdf: { bucket: 'drawings', path: revisedFile.fileName },
        upload_outputs: !!uploadOutputs,
        output: uploadOutputs ? { bucket: 'drawings', prefix: outputPrefix } : undefined,
        metadata: {
          user_id: userId,
          baseline_file_id: baselineFileId,
          revised_file_id: revisedFileId,
          drawing_number: drawingNumber,
          comparison_id: comparisonId,
        },
        comparison_id: comparisonId,
      };
      if (dpi) payload.dpi = dpi;
      if (debug !== undefined) payload.debug = !!debug;

      const apiUrl = process.env.COMPARE_API_URL || 'http://localhost:8000/compare/pdf';
      const extRes = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const extJson = await extRes.json().catch(() => ({}));
      if (!extRes.ok) {
        // Mark failed
        await storage.updateComparison(comparisonId, { status: 'failed' });
        return res.status(502).json({ message: 'Compare service failed', details: extJson, comparison_id: comparisonId });
      }

      // Update comparison with results if provided
      try {
        const updatedCore: any = { status: 'completed' };
        if (extJson?.results?.kpis) updatedCore.kpis = extJson.results.kpis;
        if (extJson?.results?.changes) updatedCore.changes = extJson.results.changes;
        // Extract page mapping from results (required)
        const pageMapping = (extJson?.results?.page_mapping || extJson?.results?.pageMapping);
        if (Array.isArray(pageMapping)) {
          updatedCore.pageMapping = pageMapping;
        }
        // capture per-page info if provided by backend under page_info or pageInfo
        const pageInfo = (extJson?.results?.page_info || extJson?.results?.pageInfo);
        if (pageInfo && typeof pageInfo === 'object') {
          updatedCore.pageInfo = pageInfo;
        }
        // optional: all pages overlay PDFs are uploaded and ready
        if (typeof extJson?.results?.all_pages_ready === 'boolean') {
          updatedCore.allPagesReady = !!extJson.results.all_pages_ready;
        } else if (typeof extJson?.all_pages_ready === 'boolean') {
          updatedCore.allPagesReady = !!extJson.all_pages_ready;
        }
        if (extJson?.results?.drawing_number) updatedCore.drawingNumber = extJson.results.drawing_number;
        await storage.updateComparison(comparisonId, updatedCore);
      } catch (_) {}

      // Attempt to persist optional AI metadata separately so a missing column won't block core fields
      try {
        const updatedAi: any = {};
        // prefer openai_threads map; fallback to single id into a one-key map if drawing number available
        if (extJson?.openai_threads && typeof extJson.openai_threads === 'object') {
          updatedAi.openaiThreads = extJson.openai_threads;
        } else if (extJson?.openai_thread_id) {
          const code = (extJson?.results?.drawing_number || 'default') as string;
          updatedAi.openaiThreads = { [code]: extJson.openai_thread_id };
        }
        if (extJson?.analysis_summary) updatedAi.analysisSummary = extJson.analysis_summary;
        if (Object.keys(updatedAi).length > 0) {
          await storage.updateComparison(comparisonId, updatedAi);
        }
      } catch (_) {}

      return res.json({ ...extJson, comparison_id: comparisonId });
    } catch (error) {
      console.error('Compare proxy error:', error);
      res.status(500).json({ message: 'Failed to run comparison', error: (error as any)?.message });
    }
  });

  // Assistants follow-up proxy
  app.post('/api/assistants/followup', requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });

      const { comparison_id, message } = req.body || {};
      if (!comparison_id || !message) {
        return res.status(400).json({ message: 'comparison_id and message are required' });
      }

      const comparison = await storage.getComparison(comparison_id);
      if (!comparison || comparison.userId !== userId) {
        return res.status(404).json({ message: 'Comparison not found' });
      }

      const baseUrl = process.env.COMPARE_API_URL || 'http://localhost:8000/compare/pdf';
      const url = new URL(baseUrl);
      // point to /assistants/followup on same host
      url.pathname = '/assistants/followup';

      const payload: any = {
        supabase: {
          url: process.env.SUPABASE_URL,
          key: process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY,
        },
        comparison_id,
        message,
      };

      const extRes = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const ct = extRes.headers.get('content-type') || '';
      let payloadOut: any = null;
      if (ct.includes('application/json')) {
        payloadOut = await extRes.json().catch(() => null);
      } else {
        const text = await extRes.text().catch(() => '');
        payloadOut = { ok: extRes.ok, raw: text };
      }
      if (!extRes.ok) {
        return res.status(extRes.status || 502).json({ ok: false, error: 'Assistants followup failed', details: payloadOut });
      }

      // Do not persist thread ids from here; FastAPI backend owns threads management

      return res.json(payloadOut ?? { ok: true });
    } catch (error) {
      console.error('Assistants followup error:', error);
      res.status(500).json({ ok: false, error: (error as any)?.message });
    }
  });

  // Get all comparisons for a user
  app.get("/api/comparisons", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const comparisons = await storage.getUserComparisons(userId);
      // Attach display names for client (prefer originalName; fallback to last segment of storage path)
      const enriched = await Promise.all(
        comparisons.map(async (c) => {
          try {
            const baseFile = await storage.getUploadedFile(c.baselineFileId);
            const revFile = await storage.getUploadedFile(c.revisedFileId);
            const baseDisplay = baseFile?.originalName || (baseFile?.fileName ? baseFile.fileName.split('/').pop() : undefined);
            const revDisplay = revFile?.originalName || (revFile?.fileName ? revFile.fileName.split('/').pop() : undefined);
            return {
              ...c,
              baselineOriginalName: baseFile?.originalName,
              revisedOriginalName: revFile?.originalName,
              baselineDisplayName: baseDisplay,
              revisedDisplayName: revDisplay,
            };
          } catch (_) {
            return c as any;
          }
        })
      );
      res.json(enriched);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch comparisons" });
    }
  });

  // Get a specific comparison
  app.get("/api/comparisons/:id", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const comparison = await storage.getComparison(req.params.id);
      if (!comparison || comparison.userId !== userId) {
        return res.status(404).json({ message: "Comparison not found" });
      }
      // Attach original file names for client display
      try {
        const baseFile = await storage.getUploadedFile(comparison.baselineFileId);
        const revFile = await storage.getUploadedFile(comparison.revisedFileId);
        const baseDisplay = baseFile?.originalName || (baseFile?.fileName ? baseFile.fileName.split('/').pop() : undefined);
        const revDisplay = revFile?.originalName || (revFile?.fileName ? revFile.fileName.split('/').pop() : undefined);
        return res.json({
          ...comparison,
          baselineOriginalName: baseFile?.originalName,
          revisedOriginalName: revFile?.originalName,
          baselineDisplayName: baseDisplay,
          revisedDisplayName: revDisplay,
        });
      } catch (_) {
        return res.json(comparison);
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch comparison" });
    }
  });

  // Get signed URL for server-generated overlay PDF if available
  app.get("/api/comparisons/:id/overlay", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const comparison = await storage.getComparison(req.params.id);
      if (!comparison || comparison.userId !== userId) {
        return res.status(404).json({ message: "Comparison not found" });
      }

      const prefix = `overlays/${userId}/${comparison.id}`;
      const code: string | undefined = typeof req.query.code === 'string' ? req.query.code : undefined;

      // Deterministic resolution using page index file naming: {oldIdx}_{newIdx}_overlay.pdf
      const matches: any[] | undefined = Array.isArray((comparison as any)?.pageMapping)
        ? ((comparison as any).pageMapping as any[])
        : undefined;

      const toIndex = (val: unknown): number | undefined => {
        if (typeof val === 'number' && Number.isInteger(val)) return val;
        if (typeof val === 'string') {
          const parsed = parseInt(val, 10);
          return Number.isFinite(parsed) ? parsed : undefined;
        }
        return undefined;
      };

      // helper: verify object existence before signing
      const fileExists = async (fullPath: string): Promise<boolean> => {
        const idx = fullPath.lastIndexOf('/');
        const dir = idx > 0 ? fullPath.slice(0, idx) : '';
        const name = idx >= 0 ? fullPath.slice(idx + 1) : fullPath;
        const { data, error } = await supabaseServer.storage
          .from('drawings')
          .list(dir);
        if (error) return false;
        return Array.isArray(data) && data.some((obj: any) => obj?.name === name);
      };

      if (code) {
        const target = String(code);
        const hit = Array.isArray(matches)
          ? matches.find((m: any) => Array.isArray(m) && String(m[0]) === target)
          : undefined;
        const oldIdx = hit ? toIndex(hit[1]) : undefined;
        const newIdx = hit ? toIndex(hit[2]) : undefined;
        if (oldIdx === undefined || newIdx === undefined) {
          return res.status(404).json({ message: 'Overlay mapping not found for specified code' });
        }
        const p = `${prefix}/${oldIdx}_${newIdx}_overlay.pdf`;
        if (!(await fileExists(p))) {
          return res.status(404).json({ message: 'Overlay not ready for specified code' });
        }
        const { data, error } = await supabaseServer.storage
          .from('drawings')
          .createSignedUrl(p, 600, { download: 'overlay.pdf' });
        if (data?.signedUrl && !error) {
          return res.json({ url: data.signedUrl, path: p });
        }
        return res.status(404).json({ message: 'Overlay not ready for specified code' });
      }

      // No code provided: only valid for single-page comparisons (exactly one mapping)
      if (!Array.isArray(matches) || matches.length === 0) {
        return res.status(404).json({ message: 'Overlay not ready' });
      }
      const uniqueCodes = new Set<string>();
      for (const m of matches) {
        if (Array.isArray(m) && typeof m[0] === 'string') uniqueCodes.add(m[0]);
      }
      if (uniqueCodes.size !== 1) {
        return res.status(400).json({ message: 'code is required for multi-page comparisons' });
      }
      const [onlyMatch] = matches;
      const onlyOld = toIndex(onlyMatch?.[1]);
      const onlyNew = toIndex(onlyMatch?.[2]);
      if (onlyOld === undefined || onlyNew === undefined) {
        return res.status(404).json({ message: 'Overlay not ready' });
      }
      const p = `${prefix}/${onlyOld}_${onlyNew}_overlay.pdf`;
      if (!(await fileExists(p))) {
        return res.status(404).json({ message: 'Overlay not ready' });
      }
      const { data, error } = await supabaseServer.storage
        .from('drawings')
        .createSignedUrl(p, 600, { download: 'overlay.pdf' });
      if (data?.signedUrl && !error) {
        return res.json({ url: data.signedUrl, path: p });
      }
      return res.status(404).json({ message: 'Overlay not ready' });
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch overlay', error: (error as any)?.message });
    }
  });

  // Create a new comparison
  app.post("/api/comparisons", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      
      // Validate that the user owns both files
      const baselineFile = await storage.getUploadedFile(req.body.baselineFileId);
      const revisedFile = await storage.getUploadedFile(req.body.revisedFileId);
      
      if (!baselineFile || !revisedFile || 
          baselineFile.userId !== userId || revisedFile.userId !== userId) {
        return res.status(400).json({ message: "Invalid file references" });
      }
      
      const validatedData = insertComparisonSchema.parse({
        ...req.body,
        userId,
      });
      
      const comparison = await storage.createComparison(validatedData);
      res.status(201).json(comparison);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid request data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create comparison" });
    }
  });

  // Update comparison status/results
  app.patch("/api/comparisons/:id", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const existing = await storage.getComparison(req.params.id);
      if (!existing || existing.userId !== userId) {
        return res.status(404).json({ message: "Comparison not found" });
      }

      const comparison = await storage.updateComparison(req.params.id, req.body);
      res.json(comparison);
    } catch (error) {
      res.status(500).json({ message: "Failed to update comparison" });
    }
  });

  // Delete a comparison
  app.delete("/api/comparisons/:id", requireAuth, async (req: any, res) => {
    try {
      const userId = req.auth!.userId;
      await storage.upsertUser({ id: userId, email: req.auth?.email ?? undefined });
      const existing = await storage.getComparison(req.params.id);
      if (!existing || existing.userId !== userId) {
        return res.status(404).json({ message: "Comparison not found" });
      }

      const success = await storage.deleteComparison(req.params.id);
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ message: "Failed to delete comparison" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
