'use client';

import React, {useEffect, useRef} from 'react';
import {Collaborator} from '@/lib/collaborator-cursor';

interface CollaboratorCursorProps {
    collaborator: Collaborator;
    editorElement: HTMLElement | null;
}

/**
 * 协作者光标组件
 * 在编辑器中显示其他用户的光标位置和选区
 */
export default function CollaboratorCursor({collaborator, editorElement}: CollaboratorCursorProps) {
    const cursorRef = useRef<HTMLDivElement>(null);
    const labelRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!editorElement || !cursorRef.current || !labelRef.current) return;

        // 获取光标位置
        const position = collaborator.position;
        if (position === undefined || position === null) return;

        try {
            // 使用 Range API 获取光标位置的坐标
            const range = document.createRange();
            const textNodes = getTextNodes(editorElement);

            let currentPos = 0;
            let targetNode: Node | null = null;
            let offset = 0;

            // 找到对应位置的文本节点
            for (const node of textNodes) {
                const nodeLength = node.textContent?.length || 0;
                if (currentPos + nodeLength >= position) {
                    targetNode = node;
                    offset = position - currentPos;
                    break;
                }
                currentPos += nodeLength;
            }

            if (!targetNode) return;

            // 设置range位置
            range.setStart(targetNode, offset);
            range.collapse(true);

            const rect = range.getBoundingClientRect();
            const editorRect = editorElement.getBoundingClientRect();

            // 更新光标位置
            cursorRef.current.style.left = `${rect.left - editorRect.left}px`;
            cursorRef.current.style.top = `${rect.top - editorRect.top}px`;
            cursorRef.current.style.height = `${rect.height}px`;
            cursorRef.current.style.backgroundColor = collaborator.color;

            // 更新标签位置
            labelRef.current.style.left = `${rect.left - editorRect.left}px`;
            labelRef.current.style.top = `${rect.top - editorRect.top - 24}px`;
            labelRef.current.style.backgroundColor = collaborator.color;

            // 如果有选区，显示选区高亮
            if (collaborator.selection && collaborator.selection.from !== collaborator.selection.to) {
                showSelection(collaborator.selection, editorElement, collaborator.color);
            }
        } catch (error) {
            console.error('Error rendering collaborator cursor:', error);
        }
    }, [collaborator, editorElement]);

    // 获取所有文本节点
    const getTextNodes = (element: HTMLElement): Text[] => {
        const textNodes: Text[] = [];
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null
        );

        let node: Node | null;
        while ((node = walker.nextNode())) {
            if (node.textContent && node.textContent.trim()) {
                textNodes.push(node as Text);
            }
        }

        return textNodes;
    };

    // 显示选区高亮
    const showSelection = (
        selection: { from: number; to: number },
        editorElement: HTMLElement,
        color: string
    ) => {
        // TODO: 实现选区高亮显示
        // 这里可以使用装饰器或mark来高亮显示选区
    };

    if (!collaborator.position && !collaborator.selection) {
        return null;
    }

    return (
        <>
            {/* 光标 */}
            <div
                ref={cursorRef}
                className="absolute w-0.5 pointer-events-none z-50 transition-all duration-100"
                style={{
                    display: collaborator.position ? 'block' : 'none',
                }}
            />

            {/* 用户名标签 */}
            <div
                ref={labelRef}
                className="absolute px-2 py-1 rounded text-xs text-white font-medium whitespace-nowrap pointer-events-none z-50 shadow-sm transition-all duration-100"
                style={{
                    display: collaborator.position ? 'block' : 'none',
                    transform: 'translateX(-50%)',
                }}
            >
                {collaborator.name}
            </div>
        </>
    );
}
