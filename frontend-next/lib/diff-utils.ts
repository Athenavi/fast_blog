/**
 * 文本差异对比工具
 * 提供行级和字符级的差异检测
 */

export interface DiffLine {
    type: 'added' | 'removed' | 'unchanged';
    content: string;
    lineNumber?: number;
    charDiffs?: CharDiff[]; // 字符级差异
}

export interface CharDiff {
    type: 'added' | 'removed' | 'unchanged';
    text: string;
}

export interface DiffResult {
    lines: DiffLine[];
    addedCount: number;
    removedCount: number;
    unchangedCount: number;
}

/**
 * 简单的行级差异对比算法
 * 基于最长公共子序列(LCS)算法的简化版本
 */
export function computeDiff(oldText: string, newText: string): DiffResult {
    const oldLines = oldText.split('\n');
    const newLines = newText.split('\n');

    // 计算LCS矩阵
    const m = oldLines.length;
    const n = newLines.length;
    const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldLines[i - 1] === newLines[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    // 回溯找出差异
    const lines: DiffLine[] = [];
    let i = m;
    let j = n;
    let addedCount = 0;
    let removedCount = 0;
    let unchangedCount = 0;

    const result: DiffLine[] = [];

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
            // 相同的行
            result.unshift({
                type: 'unchanged',
                content: oldLines[i - 1],
                lineNumber: i
            });
            unchangedCount++;
            i--;
            j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            // 新增的行
            const lineContent = newLines[j - 1];

            // 尝试找到对应的删除行，进行字符级比较
            let charDiffs: CharDiff[] | undefined;
            if (i > 0) {
                charDiffs = computeCharDiff(oldLines[i - 1], lineContent);
            }

            result.unshift({
                type: 'added',
                content: lineContent,
                charDiffs
            });
            addedCount++;
            j--;
        } else {
            // 删除的行
            const lineContent = oldLines[i - 1];

            // 尝试找到对应的新增行，进行字符级比较
            let charDiffs: CharDiff[] | undefined;
            if (j > 0) {
                charDiffs = computeCharDiff(lineContent, newLines[j - 1]);
            }

            result.unshift({
                type: 'removed',
                content: lineContent,
                charDiffs
            });
            removedCount++;
            i--;
        }
    }

    return {
        lines: result,
        addedCount,
        removedCount,
        unchangedCount
    };
}

/**
 * 字符级差异计算
 * 使用简化的 Myers 差分算法
 */
function computeCharDiff(oldText: string, newText: string): CharDiff[] {
    const oldChars = oldText.split('');
    const newChars = newText.split('');

    const m = oldChars.length;
    const n = newChars.length;

    // 对于短文本，使用简单的 LCS
    if (m < 50 && n < 50) {
        return computeSimpleCharDiff(oldChars, newChars);
    }

    // 对于长文本，使用单词级别的比较
    return computeWordLevelDiff(oldText, newText);
}

/**
 * 简单字符级差异（适用于短文本）
 */
function computeSimpleCharDiff(oldChars: string[], newChars: string[]): CharDiff[] {
    const m = oldChars.length;
    const n = newChars.length;
    const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldChars[i - 1] === newChars[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    const result: CharDiff[] = [];
    let i = m;
    let j = n;

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldChars[i - 1] === newChars[j - 1]) {
            result.unshift({type: 'unchanged', text: oldChars[i - 1]});
            i--;
            j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            result.unshift({type: 'added', text: newChars[j - 1]});
            j--;
        } else {
            result.unshift({type: 'removed', text: oldChars[i - 1]});
            i--;
        }
    }

    return result;
}

/**
 * 单词级别差异（适用于长文本）
 */
function computeWordLevelDiff(oldText: string, newText: string): CharDiff[] {
    const oldWords = oldText.split(/(\s+)/);
    const newWords = newText.split(/(\s+)/);

    const m = oldWords.length;
    const n = newWords.length;
    const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldWords[i - 1] === newWords[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    const result: CharDiff[] = [];
    let i = m;
    let j = n;

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
            result.unshift({type: 'unchanged', text: oldWords[i - 1]});
            i--;
            j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            result.unshift({type: 'added', text: newWords[j - 1]});
            j--;
        } else {
            result.unshift({type: 'removed', text: oldWords[i - 1]});
            i--;
        }
    }

    return result;
}

/**
 * 格式化差异为HTML
 */
export function formatDiffAsHtml(diff: DiffResult, showCharDiff: boolean = true): string {
    let html = '<div class="diff-viewer">';

    diff.lines.forEach((line, index) => {
        const lineClass = line.type === 'added'
            ? 'bg-green-50 dark:bg-green-950/20 text-green-800 dark:text-green-200'
            : line.type === 'removed'
                ? 'bg-red-50 dark:bg-red-950/20 text-red-800 dark:text-red-200'
                : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300';

        const prefix = line.type === 'added'
            ? '+'
            : line.type === 'removed'
                ? '-'
                : ' ';

        // 如果有字符级差异且需要显示
        let contentHtml = escapeHtml(line.content);
        if (showCharDiff && line.charDiffs && line.charDiffs.length > 0) {
            contentHtml = formatCharDiffs(line.charDiffs);
        }

        html += `
            <div class="${lineClass} px-4 py-1 font-mono text-sm whitespace-pre-wrap border-l-4 ${
            line.type === 'added'
                ? 'border-green-500'
                : line.type === 'removed'
                    ? 'border-red-500'
                    : 'border-transparent'
        }">
                <span class="inline-block w-6 text-gray-400 select-none">${prefix}</span>
                ${contentHtml}
            </div>
        `;
    });

    html += '</div>';
    return html;
}

/**
 * 格式化字符级差异
 */
function formatCharDiffs(charDiffs: CharDiff[]): string {
    let html = '';

    charDiffs.forEach(diff => {
        if (diff.type === 'unchanged') {
            html += escapeHtml(diff.text);
        } else if (diff.type === 'added') {
            html += `<mark class="bg-green-200 dark:bg-green-800 text-green-900 dark:text-green-100 px-0.5 rounded">${escapeHtml(diff.text)}</mark>`;
        } else if (diff.type === 'removed') {
            html += `<mark class="bg-red-200 dark:bg-red-800 text-red-900 dark:text-red-100 px-0.5 rounded line-through">${escapeHtml(diff.text)}</mark>`;
        }
    });

    return html;
}

/**
 * 转义HTML特殊字符
 */
function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 生成差异摘要
 */
export function getDiffSummary(diff: DiffResult): string {
    const parts = [];
    if (diff.addedCount > 0) {
        parts.push(`${diff.addedCount} 行新增`);
    }
    if (diff.removedCount > 0) {
        parts.push(`${diff.removedCount} 行删除`);
    }
    return parts.join('，') || '无变化';
}

/**
 * 导出差异为文本格式
 */
export function exportDiffAsText(diff: DiffResult, oldTitle: string = '旧版本', newTitle: string = '新版本'): string {
    let text = `差异对比报告\n`;
    text += `${'='.repeat(60)}\n\n`;
    text += `旧版本: ${oldTitle}\n`;
    text += `新版本: ${newTitle}\n`;
    text += `统计: ${getDiffSummary(diff)}\n\n`;
    text += `${'-'.repeat(60)}\n\n`;

    diff.lines.forEach(line => {
        const prefix = line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' ';
        text += `${prefix} ${line.content}\n`;
    });

    return text;
}

/**
 * 导出差异为 Markdown 格式
 */
export function exportDiffAsMarkdown(diff: DiffResult, oldTitle: string = '旧版本', newTitle: string = '新版本'): string {
    let md = `# 差异对比报告\n\n`;
    md += `- **旧版本**: ${oldTitle}\n`;
    md += `- **新版本**: ${newTitle}\n`;
    md += `- **变更**: ${getDiffSummary(diff)}\n\n`;
    md += `## 详细内容\n\n`;
    md += '```diff\n';

    diff.lines.forEach(line => {
        const prefix = line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' ';
        md += `${prefix}${line.content}\n`;
    });

    md += '```\n';
    return md;
}
