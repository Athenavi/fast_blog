/**
 * AI写作助手服务
 * 提供AI辅助写作功能
 */

export interface AISuggestion {
    id: string;
    type: 'completion' | 'rewrite' | 'expand' | 'summarize' | 'translate';
    content: string;
    confidence: number;
}

export interface AIRequest {
    action: 'complete' | 'rewrite' | 'expand' | 'summarize' | 'translate';
    text: string;
    context?: string;
    language?: string;
    tone?: 'formal' | 'casual' | 'professional' | 'friendly';
    length?: 'short' | 'medium' | 'long';
}

export class AIWritingService {
    private apiUrl: string;

    constructor(apiUrl: string = '/api/v1/ai') {
        this.apiUrl = apiUrl;
    }

    /**
     * 文本补全 - 根据上下文预测下一段内容
     */
    async completeText(context: string, maxLength: number = 200): Promise<string> {
        try {
            const response = await fetch(`${this.apiUrl}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    context,
                    max_length: maxLength,
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.completion;
            } else {
                throw new Error(data.error || '文本补全失败');
            }
        } catch (error) {
            console.error('AI文本补全错误:', error);
            // 返回模拟数据用于演示
            return this.mockCompletion(context);
        }
    }

    /**
     * 重写文本 - 改进表达方式
     */
    async rewriteText(text: string, options: {
        tone?: 'formal' | 'casual' | 'professional' | 'friendly';
        length?: 'shorter' | 'same' | 'longer';
    } = {}): Promise<string> {
        try {
            const response = await fetch(`${this.apiUrl}/rewrite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text,
                    tone: options.tone || 'professional',
                    length: options.length || 'same',
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.rewritten;
            } else {
                throw new Error(data.error || '文本重写失败');
            }
        } catch (error) {
            console.error('AI文本重写错误:', error);
            return this.mockRewrite(text);
        }
    }

    /**
     * 扩展文本 - 基于简短描述生成详细内容
     */
    async expandText(prompt: string, targetLength: number = 500): Promise<string> {
        try {
            const response = await fetch(`${this.apiUrl}/expand`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt,
                    target_length: targetLength,
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.expanded;
            } else {
                throw new Error(data.error || '文本扩展失败');
            }
        } catch (error) {
            console.error('AI文本扩展错误:', error);
            return this.mockExpand(prompt);
        }
    }

    /**
     * 生成摘要 - 提取文章关键信息
     */
    async summarizeText(text: string, maxLength: number = 150): Promise<string> {
        try {
            const response = await fetch(`${this.apiUrl}/summarize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text,
                    max_length: maxLength,
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.summary;
            } else {
                throw new Error(data.error || '文本摘要失败');
            }
        } catch (error) {
            console.error('AI文本摘要错误:', error);
            return this.mockSummarize(text);
        }
    }

    /**
     * 翻译文本
     */
    async translateText(text: string, targetLanguage: string = 'en'): Promise<string> {
        try {
            const response = await fetch(`${this.apiUrl}/translate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text,
                    target_language: targetLanguage,
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.translation;
            } else {
                throw new Error(data.error || '文本翻译失败');
            }
        } catch (error) {
            console.error('AI文本翻译错误:', error);
            return `[Translated to ${targetLanguage}]: ${text}`;
        }
    }

    /**
     * 生成标题建议
     */
    async generateTitles(content: string, count: number = 5): Promise<string[]> {
        try {
            const response = await fetch(`${this.apiUrl}/generate-titles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content,
                    count,
                }),
            });

            const data = await response.json();

            if (data.success) {
                return data.data.titles;
            } else {
                throw new Error(data.error || '标题生成失败');
            }
        } catch (error) {
            console.error('AI标题生成错误:', error);
            return this.mockGenerateTitles(content, count);
        }
    }

    // 模拟数据（用于演示和测试）
    private mockCompletion(context: string): string {
        const completions = [
            ' 这是一个很好的观点，我们可以进一步探讨...',
            ' 根据最新的研究数据显示...',
            ' 在实际应用中，我们需要注意以下几点...',
            ' 这个技术的应用前景非常广阔...',
        ];
        return completions[Math.floor(Math.random() * completions.length)];
    }

    private mockRewrite(text: string): string {
        return `【重写版本】${text}（更加专业和流畅的表达方式）`;
    }

    private mockExpand(prompt: string): string {
        return `${prompt}\n\n详细展开的内容：\n1. 第一点详细说明...\n2. 第二点详细说明...\n3. 第三点详细说明...\n\n总结：这是一个非常重要的主题。`;
    }

    private mockSummarize(text: string): string {
        const sentences = text.split(/[。！？.!?]/).filter(s => s.trim());
        return sentences.slice(0, 2).join('。') + '。';
    }

    private mockGenerateTitles(content: string, count: number): string[] {
        const baseTitles = [
            '深入解析：如何掌握这项技能',
            '完全指南：从零开始学习',
            '专家分享：最佳实践与技巧',
            '终极教程：一步步教你实现',
            '核心要点：你需要知道的一切',
        ];
        return baseTitles.slice(0, count);
    }
}

// 导出单例
export const aiWritingService = new AIWritingService();
