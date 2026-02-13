'use client';

import React, {memo} from 'react';
import {MediaFile} from '@/lib/api';

interface DeleteConfirmProps {
  item: MediaFile | null;
  onConfirm: () => void;
  onCancel: () => void;
}

const DeleteConfirm: React.FC<DeleteConfirmProps> = memo(({ item, onConfirm, onCancel }) => {
  if (!item) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onCancel}
    >
      <div className="bg-white rounded-lg shadow-lg p-6 w-96 mx-4"
           onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-medium text-gray-900 mb-2">确认删除</h3>
        <p className="text-gray-600 mb-6">
          您确定要删除 "{item.original_filename}" 吗？此操作不可撤销。
        </p>
        <div className="flex justify-end space-x-3">
          <button
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
            onClick={onCancel}
          >
            取消
          </button>
          <button
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            onClick={onConfirm}
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
});

DeleteConfirm.displayName = 'DeleteConfirm';

export default DeleteConfirm;