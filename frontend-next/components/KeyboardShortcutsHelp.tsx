'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useHotkeys } from '@/hooks/useHotkeys';

interface ShortcutItem {
  keys: string;
  description: string;
}

interface KeyboardShortcutsHelpProps {
  shortcuts: ShortcutItem[];
}

export function KeyboardShortcutsHelp({ shortcuts }: KeyboardShortcutsHelpProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Ctrl+? 或 Cmd+? 打开帮助
  useHotkeys({
    'ctrl+?': () => setIsOpen(true),
    'ctrl+/': () => setIsOpen(true),
  });

  // Esc 关闭
  useHotkeys({
    'escape': () => setIsOpen(false),
  }, isOpen);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6 relative">
        <button
          onClick={() => setIsOpen(false)}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <X size={20} />
        </button>

        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">键盘快捷键</h2>
        
        <div className="space-y-3 max-h-[60vh] overflow-y-auto">
          {shortcuts.map((item, index) => (
            <div key={index} className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">{item.description}</span>
              <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600">
                {item.keys}
              </kbd>
            </div>
          ))}
        </div>

        <div className="mt-6 text-xs text-gray-500 dark:text-gray-400 text-center">
          按 <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">Esc</kbd> 关闭
        </div>
      </div>
    </div>
  );
}
