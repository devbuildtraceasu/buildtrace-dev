import { supabase } from "@/lib/supabaseClient";
import * as pdfjsLib from "pdfjs-dist";
import workerSrcUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrcUrl as unknown as string;

export interface PdfDocumentHandle {
  id: string;
  numPages: number;
}

type InternalDoc = {
  doc: any; // PDFDocumentProxy
};

export interface IPdfService {
  load(fileUrl: string): Promise<PdfDocumentHandle>;
  renderPage(container: HTMLElement, handle: PdfDocumentHandle, page: number, scalePercent: number): Promise<void>;
  renderPageAtDisplaySize(
    container: HTMLElement,
    handle: PdfDocumentHandle,
    page: number,
    baseDisplayWidthPx: number,
    zoomPercent: number,
  ): Promise<void>;
  dispose(handle: PdfDocumentHandle): void;
  preload(fileUrls: string[]): Promise<void>;
  getPageUnscaledSize(fileUrl: string, page: number): Promise<{ width: number; height: number }>;
}

export class PdfService implements IPdfService {
  private documentsByUrl: Map<string, InternalDoc> = new Map();

  async load(fileUrl: string): Promise<PdfDocumentHandle> {
    // Return cached doc if available
    const cached = this.documentsByUrl.get(fileUrl);
    if (cached) {
      return { id: fileUrl, numPages: cached.doc.numPages };
    }

    // Attach Supabase auth for app-protected endpoints (signed URLs don't need it)
    const session = await supabase.auth.getSession();
    const accessToken = session.data.session?.access_token;

    const loadingTask = pdfjsLib.getDocument({
      url: fileUrl,
      httpHeaders: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      withCredentials: false,
    } as any);

    const doc = await loadingTask.promise;
    this.documentsByUrl.set(fileUrl, { doc });

    return { id: fileUrl, numPages: doc.numPages };
  }

  async renderPage(container: HTMLElement, handle: PdfDocumentHandle, page: number, scalePercent: number): Promise<void> {
    const internal = this.documentsByUrl.get(handle.id);
    if (!internal) return;

    const pdfPage = await internal.doc.getPage(page);
    const baseScale = Math.max(0.1, (scalePercent || 100) / 100);
    // Compute scale to fit container width for crisp rendering
    const unscaled = pdfPage.getViewport({ scale: 1 });
    const containerWidth = Math.max(1, container.clientWidth || unscaled.width);
    const fitScale = containerWidth / unscaled.width;
    const finalScale = baseScale * fitScale;
    const viewport = pdfPage.getViewport({ scale: finalScale });

    // Prepare canvas
    container.innerHTML = "";
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.floor(viewport.width * dpr);
    canvas.height = Math.floor(viewport.height * dpr);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;
    container.appendChild(canvas);
    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    const renderContext = { canvasContext: context, viewport } as any;
    await pdfPage.render(renderContext).promise;
  }

  async renderPageAtDisplaySize(
    container: HTMLElement,
    handle: PdfDocumentHandle,
    page: number,
    baseDisplayWidthPx: number,
    zoomPercent: number,
  ): Promise<void> {
    const internal = this.documentsByUrl.get(handle.id);
    if (!internal) return;

    const pdfPage = await internal.doc.getPage(page);
    const unscaled = pdfPage.getViewport({ scale: 1 });
    const baseScale = Math.max(0.01, baseDisplayWidthPx / unscaled.width);
    const zoomScale = Math.max(0.1, (zoomPercent || 100) / 100);
    // Keep viewport at base scale so CSS box stays constant; increase pixel density via DPR*zoom
    const viewport = pdfPage.getViewport({ scale: baseScale });

    // Prepare canvas with DPR for crisp vector rendering
    container.innerHTML = "";
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1) * zoomScale;
    canvas.width = Math.floor(viewport.width * dpr);
    canvas.height = Math.floor(viewport.height * dpr);

    // Keep displayed size fixed to base dimensions so wrapper height does not change
    const displayHeightPx = Math.floor(unscaled.height * baseScale);
    canvas.style.width = `${Math.floor(baseDisplayWidthPx)}px`;
    canvas.style.height = `${displayHeightPx}px`;

    container.appendChild(canvas);
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    const renderContext = { canvasContext: context, viewport } as any;
    await pdfPage.render(renderContext).promise;
  }

  dispose(handle: PdfDocumentHandle): void {
    // Keep documents cached for the session to enable instant view toggles
    // No-op for now; a TTL-based eviction could be added later
  }

  async preload(fileUrls: string[]): Promise<void> {
    await Promise.all(
      fileUrls
        .filter(Boolean)
        .map(async (url) => {
          try {
            await this.load(url);
          } catch (_err) {
            // ignore preload failures; viewer will attempt again on demand
          }
        })
    );
  }

  async getPageUnscaledSize(fileUrl: string, page: number): Promise<{ width: number; height: number }> {
    // Ensure document is loaded (and cached)
    await this.load(fileUrl);
    const internal = this.documentsByUrl.get(fileUrl);
    if (!internal) return { width: 0, height: 0 };
    const pdfPage = await internal.doc.getPage(page);
    const viewport = pdfPage.getViewport({ scale: 1 });
    return { width: viewport.width, height: viewport.height } as { width: number; height: number };
  }
}

export const pdfService = new PdfService();
