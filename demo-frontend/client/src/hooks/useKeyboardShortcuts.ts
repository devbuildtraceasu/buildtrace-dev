import { useEffect } from "react";

export function useKeyboardShortcuts(shortcuts: Record<string, () => void>) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      const ctrl = event.ctrlKey || event.metaKey;
      const shift = event.shiftKey;
      const alt = event.altKey;

      let keyCombo = '';
      if (ctrl) keyCombo += 'ctrl+';
      if (shift) keyCombo += 'shift+';
      if (alt) keyCombo += 'alt+';
      keyCombo += key;

      if (shortcuts[keyCombo]) {
        event.preventDefault();
        shortcuts[keyCombo]();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}
