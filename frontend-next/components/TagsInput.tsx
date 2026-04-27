'use client';

import React, {useCallback, useState} from 'react';

interface TagsInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
}

const TagsInput: React.FC<TagsInputProps> = ({ value, onChange }) => {
  const [input, setInput] = useState('');

  const handleAdd = useCallback(() => {
    const trimmed = input.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
      setInput('');
    }
  }, [input, value, onChange]);

  const handleRemove = useCallback((tagToRemove: string) => {
    onChange(value.filter(tag => tag !== tagToRemove));
  }, [value, onChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {value.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm font-medium dark:bg-blue-900/30 dark:text-blue-300"
          >
            {tag}
            <button
              type="button"
              onClick={() => handleRemove(tag)}
              className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-lg leading-none"
              aria-label={`移除标签 ${tag}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleAdd}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
          placeholder="输入标签，按回车添加"
        />
        <button
          type="button"
          onClick={handleAdd}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          添加
        </button>
      </div>
    </div>
  );
};

export default TagsInput;