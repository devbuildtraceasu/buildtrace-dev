import { useEffect, useRef, useState } from "react";
import { pdfService, PdfDocumentHandle } from "./PdfService";

interface PdfViewerProps {
  fileUrl?: string;
  scale?: number;
  page?: number;
  className?: string;
  onPanChange?: (scrollLeft: number, scrollTop: number) => void;
  externalPanLeft?: number;
  externalPanTop?: number;
  onZoomChange?: (newScale: number) => void;
}

export default function PdfViewer({ 
  fileUrl, 
  scale = 100, 
  page = 1, 
  className = "",
  onPanChange,
  externalPanLeft,
  externalPanTop,
  onZoomChange
}: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const documentHandleRef = useRef<PdfDocumentHandle | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const frameRatio = 0.7727; // Approx. US Letter landscape (8.5/11)
  const isExternalPanRef = useRef(false);
  const [internalZoom, setInternalZoom] = useState(scale);
  const lastZoomTimeRef = useRef(0);
  const pinchStartRef = useRef<{ distance: number; zoom: number } | null>(null);

  // Sync internal zoom with external scale prop
  useEffect(() => {
    setInternalZoom(scale);
  }, [scale]);

  useEffect(() => {
    if (!fileUrl || !containerRef.current) return;

    const loadPdf = async () => {
      try {
        const handle = await pdfService.load(fileUrl);
        documentHandleRef.current = handle;
        
        if (containerRef.current) {
          await pdfService.renderPage(containerRef.current, handle, page, internalZoom);
        }
      } catch (error) {
        console.error("Failed to load PDF:", error);
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <div class="flex items-center justify-center h-full text-red-500">
              <div class="text-center">
                <p class="font-medium">Failed to load PDF</p>
                <p class="text-sm">${error instanceof Error ? error.message : 'Unknown error'}</p>
              </div>
            </div>
          `;
        }
      }
    };

    loadPdf();

    return () => {
      if (documentHandleRef.current) {
        pdfService.dispose(documentHandleRef.current);
      }
    };
  }, [fileUrl]);

  // Helper: set a constant frame height based on a landscape ratio
  const setFrameHeight = () => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const w = wrapper.clientWidth || wrapper.getBoundingClientRect().width || 0;
    if (w > 0) {
      const h = Math.max(1, Math.floor(w * frameRatio));
      wrapper.style.height = `${h}px`;
    }
  };

  useEffect(() => {
    setFrameHeight();
    const onResize = () => setFrameHeight();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Render page content when file or page changes at base width; zoom will re-render at higher scale (vector).
  useEffect(() => {
    const render = async () => {
      if (!documentHandleRef.current || !containerRef.current || !wrapperRef.current || !fileUrl) return;
      setFrameHeight();
      const baseWidth = wrapperRef.current.clientWidth || wrapperRef.current.getBoundingClientRect().width || 0;
      await pdfService.renderPageAtDisplaySize(containerRef.current, documentHandleRef.current, page, baseWidth, internalZoom);
      // Normalize canvas CSS size to frame on initial render
      const canvas = containerRef.current.querySelector('canvas') as HTMLCanvasElement | null;
      if (canvas) {
        const frameH = wrapperRef.current.clientHeight || wrapperRef.current.getBoundingClientRect().height || 0;
        canvas.style.width = `${Math.floor(baseWidth)}px`;
        if (frameH > 0) canvas.style.height = `${Math.floor(frameH)}px`;
      }
    };
    render();
  }, [page, fileUrl]);

  // Apply zoom by re-rendering with higher pixel density and visually scaling canvas within fixed frame
  useEffect(() => {
    const rerender = async () => {
      if (!documentHandleRef.current || !containerRef.current || !wrapperRef.current || !fileUrl) return;
      setFrameHeight();
      const baseWidth = wrapperRef.current.clientWidth || wrapperRef.current.getBoundingClientRect().width || 0;
      await pdfService.renderPageAtDisplaySize(containerRef.current, documentHandleRef.current, page, baseWidth, internalZoom);
      // Enlarge canvas CSS box while keeping the frame fixed; allows drag-to-pan
      const canvas = containerRef.current.querySelector('canvas') as HTMLCanvasElement | null;
      if (canvas) {
        const factor = Math.max(0.1, (internalZoom || 100) / 100);
        const frameW = baseWidth;
        const frameH = wrapperRef.current.clientHeight || wrapperRef.current.getBoundingClientRect().height || 0;
        canvas.style.transform = 'none';
        canvas.style.width = `${Math.floor(frameW * factor)}px`;
        if (frameH > 0) canvas.style.height = `${Math.floor(frameH * factor)}px`;
      }
    };
    rerender();
  }, [internalZoom]);

  // Reapply frame height on file or page change
  useEffect(() => {
    setFrameHeight();
  }, [fileUrl, page]);

  // Handle external pan changes
  useEffect(() => {
    if (wrapperRef.current && typeof externalPanLeft === 'number' && typeof externalPanTop === 'number') {
      isExternalPanRef.current = true;
      wrapperRef.current.scrollLeft = externalPanLeft;
      wrapperRef.current.scrollTop = externalPanTop;
      // Reset the flag after a short delay to allow for smooth updates
      setTimeout(() => {
        isExternalPanRef.current = false;
      }, 10);
    }
  }, [externalPanLeft, externalPanTop]);

  // Drag to pan (mouse)
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      setIsDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY, left: wrapper.scrollLeft, top: wrapper.scrollTop };
      e.preventDefault();
    };
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging || !dragStart.current || isExternalPanRef.current) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      wrapper.scrollLeft = dragStart.current.left - dx;
      wrapper.scrollTop = dragStart.current.top - dy;
      
      // Notify parent about pan changes
      if (onPanChange) {
        onPanChange(wrapper.scrollLeft, wrapper.scrollTop);
      }
    };
    const endDrag = () => {
      setIsDragging(false);
      dragStart.current = null;
    };
    wrapper.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', endDrag);
    return () => {
      wrapper.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', endDrag);
    };
  }, [isDragging]);

  // Touch pan
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const onTouchStart = (e: TouchEvent) => {
      const t = e.touches[0];
      if (!t) return;
      setIsDragging(true);
      dragStart.current = { x: t.clientX, y: t.clientY, left: wrapper.scrollLeft, top: wrapper.scrollTop };
    };
    const onTouchMove = (e: TouchEvent) => {
      if (!isDragging || !dragStart.current || isExternalPanRef.current) return;
      const t = e.touches[0];
      if (!t) return;
      const dx = t.clientX - dragStart.current.x;
      const dy = t.clientY - dragStart.current.y;
      wrapper.scrollLeft = dragStart.current.left - dx;
      wrapper.scrollTop = dragStart.current.top - dy;
      
      // Notify parent about pan changes
      if (onPanChange) {
        onPanChange(wrapper.scrollLeft, wrapper.scrollTop);
      }
    };
    const onTouchEnd = () => {
      setIsDragging(false);
      dragStart.current = null;
    };
    wrapper.addEventListener('touchstart', onTouchStart, { passive: true });
    wrapper.addEventListener('touchmove', onTouchMove, { passive: true });
    wrapper.addEventListener('touchend', onTouchEnd);
    return () => {
      wrapper.removeEventListener('touchstart', onTouchStart as any);
      wrapper.removeEventListener('touchmove', onTouchMove as any);
      wrapper.removeEventListener('touchend', onTouchEnd);
    };
  }, [isDragging]);

  // Mouse wheel zoom
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const handleWheel = (e: WheelEvent) => {
      // Prevent default scrolling behavior
      e.preventDefault();

      // Only zoom if Ctrl/Cmd key is held or if it's a pinch gesture (deltaY is 0 but deltaX/Y exist)
      const isZoomGesture = e.ctrlKey || e.metaKey || (e.deltaY === 0 && (e.deltaX !== 0 || Math.abs(e.deltaY) < 10));

      if (!isZoomGesture) return;

      // Throttle zoom events
      const now = Date.now();
      if (now - lastZoomTimeRef.current < 50) return;
      lastZoomTimeRef.current = now;

      // Calculate zoom direction and amount
      const zoomSpeed = 0.1;
      const zoomDirection = e.deltaY > 0 ? -1 : 1;
      const zoomAmount = 1 + (zoomDirection * zoomSpeed);

      // Calculate new zoom level with bounds
      const newZoom = Math.max(25, Math.min(500, internalZoom * zoomAmount));

      if (newZoom !== internalZoom) {
        // Get mouse position relative to wrapper
        const rect = wrapper.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Calculate mouse position in content space (before zoom)
        const contentX = wrapper.scrollLeft + mouseX;
        const contentY = wrapper.scrollTop + mouseY;

        // Calculate the scale factor
        const scaleFactor = newZoom / internalZoom;

        // Calculate new mouse position in content space (after zoom)
        const newContentX = contentX * scaleFactor;
        const newContentY = contentY * scaleFactor;

        // Calculate new scroll position to keep mouse position fixed
        const newScrollLeft = newContentX - mouseX;
        const newScrollTop = newContentY - mouseY;

        setInternalZoom(newZoom);

        // Apply the new scroll position after the zoom has been applied
        setTimeout(() => {
          if (wrapper) {
            wrapper.scrollLeft = newScrollLeft;
            wrapper.scrollTop = newScrollTop;

            // Notify parent about pan changes
            if (onPanChange) {
              onPanChange(wrapper.scrollLeft, wrapper.scrollTop);
            }
          }
        }, 0);

        // Notify parent component about zoom change
        if (onZoomChange) {
          onZoomChange(newZoom);
        }
      }
    };

    // Add wheel event listener with passive: false to allow preventDefault
    wrapper.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      wrapper.removeEventListener('wheel', handleWheel);
    };
  }, [internalZoom, onZoomChange, onPanChange]);

  // Trackpad pinch zoom
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const getDistance = (touches: TouchList) => {
      if (touches.length < 2) return 0;
      const dx = touches[0].clientX - touches[1].clientX;
      const dy = touches[0].clientY - touches[1].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    };

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        const distance = getDistance(e.touches);
        pinchStartRef.current = { distance, zoom: internalZoom };
      } else {
        pinchStartRef.current = null;
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && pinchStartRef.current) {
        e.preventDefault(); // Prevent default pinch-to-zoom behavior

        const currentDistance = getDistance(e.touches);
        const startDistance = pinchStartRef.current.distance;
        const startZoom = pinchStartRef.current.zoom;

        if (currentDistance > 0 && startDistance > 0) {
          const scale = currentDistance / startDistance;
          const newZoom = Math.max(25, Math.min(500, startZoom * scale));

          if (Math.abs(newZoom - internalZoom) > 1) {
            setInternalZoom(newZoom);

            // Notify parent component about zoom change
            if (onZoomChange) {
              onZoomChange(newZoom);
            }
          }
        }
      }
    };

    const handleTouchEnd = () => {
      pinchStartRef.current = null;
    };

    wrapper.addEventListener('touchstart', handleTouchStart, { passive: true });
    wrapper.addEventListener('touchmove', handleTouchMove, { passive: false });
    wrapper.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      wrapper.removeEventListener('touchstart', handleTouchStart);
      wrapper.removeEventListener('touchmove', handleTouchMove);
      wrapper.removeEventListener('touchend', handleTouchEnd);
    };
  }, [internalZoom, onZoomChange]);

  return (
    <div
      ref={wrapperRef}
      className={`w-full overflow-auto ${isDragging ? 'cursor-grabbing' : 'cursor-grab'} ${className}`}
      style={{ userSelect: isDragging ? 'none' as const : undefined }}
    >
      <div
        ref={containerRef}
        className="w-full inline-block"
        data-testid="pdf-viewer"
      />
    </div>
  );
}
