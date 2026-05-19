'use client';

import {useEffect, useRef, useState} from 'react';
import {Image as ImageIcon, X} from 'lucide-react';
import {EmotePicker} from './EmotePicker';
import {MentionPicker} from './MentionPicker';
import {parseEmotes} from '@/lib/emoteService';
import {useToast} from '@/hooks/use-toast';
import {userService, UserSuggestion} from '@/lib/api/user-service';

interface CommentInputProps {
  onSubmit: (content: string) => void;
  placeholder?: string;
}

export function CommentInput({ onSubmit, placeholder = '发表评论...' }: CommentInputProps) {
  const [content, setContent] = useState('');
  const [uploadedImages, setUploadedImages] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showMentionPicker, setShowMentionPicker] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionPosition, setMentionPosition] = useState({ top: 0, left: 0 });
  const [mentionStartPos, setMentionStartPos] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // 真实用户列表（从 API 获取）
  const [users, setUsers] = useState<UserSuggestion[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);

  // 当 @提及框显示时，加载用户列表
  useEffect(() => {
    if (showMentionPicker) {
      setIsLoadingUsers(true);
      userService.searchUsers(mentionQuery, 10)
          .then(result => {
            if (result.success && result.data) {
                setUsers((result.data as any).users || []);
            }
          })
          .catch(error => {
            console.error('Failed to load users:', error);
          })
          .finally(() => {
            setIsLoadingUsers(false);
          });
    }
  }, [showMentionPicker, mentionQuery]);

  // 处理表情选择
  const handleEmoteSelect = (emoteCode: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newContent = content.substring(0, start) + emoteCode + content.substring(end);
    
    setContent(newContent);
    
    // 恢复焦点并设置光标位置
    setTimeout(() => {
      textarea.focus();
      const newPos = start + emoteCode.length;
      textarea.setSelectionRange(newPos, newPos);
    }, 0);
  };

  // 检测 @提及
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPos);
    
    // 查找最后一个 @符号
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    if (lastAtIndex !== -1) {
      // 检查 @后面是否有空格或其他字符（除了字母数字下划线）
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      const match = textAfterAt.match(/^([a-zA-Z0-9_\u4e00-\u9fa5]*)$/);
      
      if (match) {
        const query = match[1];
        
        // 计算位置
        const textareaRect = textarea.getBoundingClientRect();
        const lines = textBeforeCursor.split('\n');
        const currentLineIndex = lines.length - 1;
        const lineHeight = 24; // 估计的行高
        
        setMentionQuery(query);
        setMentionStartPos(lastAtIndex);
        setMentionPosition({
          top: textareaRect.top + (currentLineIndex + 1) * lineHeight,
          left: textareaRect.left + 10,
        });
        setShowMentionPicker(true);
      } else {
        setShowMentionPicker(false);
      }
    } else {
      setShowMentionPicker(false);
    }
  }, [content]);

  // 处理用户选择
  const handleMentionSelect = (username: string) => {
    if (mentionStartPos === null) return;
    
    const textarea = textareaRef.current;
    if (!textarea) return;

    const beforeMention = content.substring(0, mentionStartPos);
    const afterCursor = content.substring(textarea.selectionStart);
    const newContent = `${beforeMention}@${username} ${afterCursor}`;
    
    setContent(newContent);
    setShowMentionPicker(false);
    setMentionStartPos(null);
    
    // 恢复焦点
    setTimeout(() => {
      textarea.focus();
      const newPos = mentionStartPos + username.length + 2; // @username + 空格
      textarea.setSelectionRange(newPos, newPos);
    }, 0);
  };

  // 处理图片上传
  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    // 检查文件数量限制
    if (uploadedImages.length + files.length > 5) {
      toast({
        title: '超出限制',
        description: '最多只能上传5张图片',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 检查文件大小（最大5MB）
        if (file.size > 5 * 1024 * 1024) {
          toast({
            title: '文件过大',
            description: `图片 "${file.name}" 超过5MB限制`,
            variant: 'destructive',
          });
          continue;
        }

        // 检查文件类型
        if (!file.type.startsWith('image/')) {
          toast({
            title: '格式不支持',
            description: `"${file.name}" 不是有效的图片文件`,
            variant: 'destructive',
          });
          continue;
        }

        // 这里应该调用实际的上传API
        // 暂时使用 FileReader 模拟上传
        const reader = new FileReader();
        reader.onloadend = () => {
          if (reader.result) {
            setUploadedImages(prev => [...prev, reader.result as string]);
          }
        };
        reader.readAsDataURL(file);
      }
    } catch (error) {
      toast({
        title: '上传失败',
        description: '图片上传失败，请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      // 清空input以便可以重复选择同一文件
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 移除已上传的图片
  const removeImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index));
  };

  // 点击上传图片按钮
  const handleImageButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleSubmit = () => {
    if (!content.trim() && uploadedImages.length === 0) return;
    
    // 如果有图片，将图片URL添加到内容中
    let finalContent = content;
    if (uploadedImages.length > 0) {
      const imageMarkdown = uploadedImages.map(url => `\n![图片](${url})`).join('');
      finalContent = content + imageMarkdown;
    }
    
    onSubmit(finalContent);
    setContent('');
    setUploadedImages([]);
  };

  return (
    <div className="relative">
      <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className="w-full p-3 resize-none focus:outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
        />
        
        {/* 工具栏 */}
        <div className="flex justify-between items-center px-3 py-2 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600">
          <div className="flex items-center gap-2">
            {/* 表情选择器 */}
            <EmotePicker onSelect={handleEmoteSelect} />
            
            {/* 图片上传按钮 */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleImageUpload}
              className="hidden"
            />
            <button
              type="button"
              onClick={handleImageButtonClick}
              disabled={isUploading}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              title="上传图片"
            >
              <ImageIcon size={20} />
            </button>
          </div>
          
          <button
            onClick={handleSubmit}
            disabled={!content.trim()}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            发表评论
          </button>
        </div>
      </div>

      {/* 实时预览 */}
      {(content || uploadedImages.length > 0) && (
        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">预览：</p>
          <div className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
            {parseEmotes(content)}
          </div>
          
          {/* 已上传图片预览 */}
          {uploadedImages.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {uploadedImages.map((img, index) => (
                <div key={index} className="relative group">
                  <img
                    src={img}
                    alt={`预览 ${index + 1}`}
                    className="w-20 h-20 object-cover rounded border border-gray-300 dark:border-gray-600"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* @提及选择器 */}
      {showMentionPicker && (
        <MentionPicker
          onSelect={handleMentionSelect}
          query={mentionQuery}
          position={mentionPosition}
          users={users}
        />
      )}
    </div>
  );
}
