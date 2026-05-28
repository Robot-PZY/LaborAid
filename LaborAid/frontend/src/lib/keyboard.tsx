import { useState, useEffect, useCallback, useContext, createContext, type ReactNode } from 'react';

/** Keyboard shortcuts context and help dialog */

interface KeyboardShortcutsContextValue {
  showHelp: boolean;
  setShowHelp: (v: boolean) => void;
}

const KeyboardShortcutsContext = createContext<KeyboardShortcutsContextValue>({
  showHelp: false,
  setShowHelp: () => {},
});

export function useKeyboardHelp() {
  return useContext(KeyboardShortcutsContext);
}

/** Global shortcut definitions */
const SHORTCUTS = [
  { keys: ['?'], description: '显示快捷键帮助', category: '通用' },
  { keys: ['Ctrl', 'Enter'], description: '提交当前表单', category: '通用' },
  { keys: ['Escape'], description: '关闭弹窗/对话框', category: '通用' },
  { keys: ['/'], description: '跳转到搜索页', category: '导航' },
];

export function KeyboardShortcutsProvider({ children }: { children: ReactNode }) {
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Show help on '?' key (but not when typing in an input)
      if (e.key === '?' && !isEditableTarget(e.target as HTMLElement)) {
        e.preventDefault();
        setShowHelp((prev) => !prev);
      }
      // Close help on Escape
      if (e.key === 'Escape' && showHelp) {
        setShowHelp(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showHelp]);

  return (
    <KeyboardShortcutsContext.Provider value={{ showHelp, setShowHelp }}>
      {children}
      {/* Shortcut Help Dialog */}
      {showHelp && (
        <div
          className="fixed inset-0 z-[150] flex items-center justify-center bg-black/50"
          onClick={() => setShowHelp(false)}
          role="dialog"
          aria-modal="true"
          aria-label="键盘快捷键"
        >
          <div
            className="w-full max-w-md rounded-xl bg-card p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold mb-4">键盘快捷键</h2>
            <div className="space-y-1">
              {SHORTCUTS.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-accent">
                  <span className="text-sm text-foreground">{s.description}</span>
                  <div className="flex items-center gap-1">
                    {s.keys.map((key, ki) => (
                      <span key={ki} className="flex items-center gap-1">
                        {ki > 0 && <span className="text-xs text-muted-foreground">+</span>}
                        <kbd className="rounded border bg-muted px-2 py-0.5 text-xs font-mono">{key}</kbd>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-muted-foreground text-center">按 <kbd className="rounded border bg-muted px-1.5 py-0.5 text-xs font-mono">?</kbd> 或 <kbd className="rounded border bg-muted px-1.5 py-0.5 text-xs font-mono">Esc</kbd> 关闭</p>
          </div>
        </div>
      )}
    </KeyboardShortcutsContext.Provider>
  );
}

/** Check if the target is an editable element (input, textarea, select) */
function isEditableTarget(el: HTMLElement): boolean {
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  return false;
}

/** Hook for Ctrl+Enter form submission */
export function useCtrlEnter(callback: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        const el = e.target as HTMLElement;
        if (el && isEditableTarget(el)) {
          e.preventDefault();
          callback();
        }
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [callback]);
}
