'use client';

import React, {useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import tocbot from 'tocbot';
import {ArticleDetailResponse} from "@/lib/api/article-service";
import DraggableToc from './DraggableToc';

interface ArticleDetailClientProps {
    articleData: ArticleDetailResponse;
}

const ArticleDetailClient: React.FC<ArticleDetailClientProps> = ({articleData}) => {
    const {article, author, i18n_versions = []} = articleData;
    const [likes, setLikes] = useState<number>(article.likes || 0);
    const [hasLiked, setHasLiked] = useState<boolean>(false);
    // 添加朗读相关状态
    const [isReading, setIsReading] = useState<boolean>(false);
    const [isPaused, setIsPaused] = useState<boolean>(false);
    const [currentSentenceIndex, setCurrentSentenceIndex] = useState<number>(0);
    const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
    const [selectedVoice, setSelectedVoice] = useState<string>('');
    const [rate, setRate] = useState<number>(1.0);
    const [pitch, setPitch] = useState<number>(1.0);
    const [showAccessibilityControls, setShowAccessibilityControls] = useState<boolean>(false);
    const [sentences, setSentences] = useState<string[]>([]);
    const [autoScroll, setAutoScroll] = useState<boolean>(true);
    const [progress, setProgress] = useState<number>(0);
    const [filterConfig, setFilterConfig] = useState({
        filterCode: true,
        filterScripts: true,
        filterHtmlTags: false,
        filterSpecialChars: false
    });
    const synthRef = useRef<SpeechSynthesis | null>(null);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const tocbotRef = useRef<any | null>(null);

    // 使用更可靠的目录生成方案
    useEffect(() => {
        if (typeof window === 'undefined' || !article.content) {
            return;
        }

        // 清理之前的实例
        if (tocbotRef.current) {
            try {
                tocbotRef.current.destroy();
            } catch (error) {
                console.warn('销毁 Tocbot 实例时出错:', error);
            }
        }

        let initAttempts = 0;
        const maxAttempts = 8;
        
        // 检查并初始化目录的函数
        const tryInitializeToc = () => {
            initAttempts++;
            console.log(`=== 目录初始化尝试 ${initAttempts}/${maxAttempts} ===`);
            
            const contentElement = contentRef.current;
            const tocContainer = document.querySelector('.js-toc');
            
            // 基本检查
            if (!contentElement || !tocContainer) {
                console.log('DOM 元素未就绪');
                return false;
            }
            
            // 检查内容是否已渲染
            if (!contentElement.innerHTML?.trim()) {
                console.log('内容尚未渲染');
                return false;
            }
            
            // 查找标题
            const headings = contentElement.querySelectorAll('h1, h2, h3, h4, h5, h6');
            console.log('找到标题数量:', headings.length);
            
            if (headings.length === 0) {
                tocContainer.innerHTML = '<p class="text-gray-500 text-sm py-4">本文无结构化标题</p>';
                return true;
            }
            
            // 检查标题元素是否已完全渲染
            let allRendered = true;
            headings.forEach((heading, index) => {
                const htmlHeading = heading as HTMLElement;
                if (!htmlHeading.offsetHeight || !htmlHeading.offsetTop) {
                    console.log(`标题 ${index} 未完全渲染`);
                    allRendered = false;
                }
            });
            
            if (!allRendered && initAttempts < maxAttempts) {
                return false;
            }
            
            try {
                // 初始化 Tocbot
                tocbot.init({
                    tocSelector: '.js-toc',
                    contentSelector: '.article-content',
                    headingSelector: 'h1, h2, h3, h4, h5, h6',
                    positionFixedSelector: '.js-toc',
                    positionFixedClass: 'is-position-fixed',
                    fixedSidebarOffset: 100,
                    includeHtml: true,
                    headingsOffset: 10,
                    ignoreSelector: '.js-toc-ignore',
                    linkClass: 'toc-link',
                    activeLinkClass: 'is-active-link',
                    listClass: 'toc-list',
                    listItemClass: 'toc-list-item',
                    collapseDepth: 0,
                    orderedList: false,
                    onClick: function (e) {
                        e.preventDefault();
                        const target = e.target as HTMLAnchorElement;
                        const targetId = target.getAttribute('href')?.substring(1);
                        if (targetId) {
                            const targetElement = document.getElementById(targetId);
                            if (targetElement) {
                                targetElement.scrollIntoView({ 
                                    behavior: 'smooth', 
                                    block: 'center' 
                                });
                                // 添加高亮效果
                                targetElement.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                                setTimeout(() => {
                                    targetElement.style.backgroundColor = '';
                                }, 1000);
                            }
                        }
                        console.log('点击目录:', (e.target as HTMLElement).textContent);
                    }
                });
                
                tocbotRef.current = tocbot;
                console.log('✅ 目录初始化成功');
                return true;
                
            } catch (error) {
                if (error instanceof Error) {
                    console.error('Tocbot 初始化失败:', error.message);
                    tocContainer.innerHTML = `<p class="text-red-500 text-sm py-4">初始化失败: ${error.message}</p>`;
                }
                return false;
            }
        };
        
        // 使用 requestAnimationFrame 确保在浏览器重绘后执行
        const scheduleInit = () => {
            if (initAttempts >= maxAttempts) {
                console.log('❌ 达到最大尝试次数');
                const tocContainer = document.querySelector('.js-toc');
                if (tocContainer) {
                    tocContainer.innerHTML = '<p class="text-gray-500 text-sm py-4">目录生成失败，请刷新重试</p>';
                }
                return;
            }
            
            requestAnimationFrame(() => {
                if (!tryInitializeToc()) {
                    // 递增延迟重试
                    const delay = Math.min(500 * Math.pow(1.5, initAttempts), 3000);
                    setTimeout(scheduleInit, delay);
                }
            });
        };
        
        // 延迟开始初始化
        const initTimer = setTimeout(scheduleInit, 1000);
        
        return () => {
            clearTimeout(initTimer);
            if (tocbotRef.current) {
                try {
                    tocbotRef.current.destroy();
                } catch (error) {
                    console.warn('清理 Tocbot 时出错:', error);
                }
            }
        };
    }, [article.content]);

    // 处理点赞功能
    const handleLike = async () => {
        if (hasLiked) return; // 防止重复点赞

        // 本地更新UI
        setLikes(prev => prev + 1);
        setHasLiked(true);

        try {
            // 发送请求到后端更新点赞数
            const response = await fetch(`/api/articles/${article.id}/like`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                // 如果请求失败，回滚本地状态
                setLikes(prev => prev - 1);
                setHasLiked(false);
                throw new Error('点赞失败');
            }
        } catch (error) {
            console.error('点赞时发生错误:', error);
            // 出错时回滚本地状态
            setLikes(prev => prev - 1);
            setHasLiked(false);
        }
    };

    // 初始化语音合成
    useEffect(() => {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            synthRef.current = window.speechSynthesis;

            const loadVoices = () => {
                const availableVoices = synthRef.current!.getVoices();
                setVoices(availableVoices);

                // 优先选择中文语音
                const chineseVoice = availableVoices.find(voice => voice.lang.startsWith('zh'));
                if (chineseVoice) {
                    setSelectedVoice(chineseVoice.name);
                } else if (availableVoices.length > 0) {
                    setSelectedVoice(availableVoices[0].name);
                }
            };

            loadVoices();
            synthRef.current.onvoiceschanged = loadVoices;

            return () => {
                if (synthRef.current) {
                    synthRef.current.onvoiceschanged = null;
                }
            };
        }
    }, []);

    // 提取文章内容中的句子
    const extractSentences = (): string[] => {
        if (!contentRef.current) return [];

        // 深度克隆DOM节点
        const contentClone = contentRef.current.cloneNode(true) as HTMLElement;

        // 移除不需要的元素
        const elementsToRemove = [
            'script', 'style', 'noscript', 'template',
            'pre', 'code', 'kbd', 'samp', 'var',
            'button', 'input', 'textarea', 'select', 'option', 'form',
            'img', 'audio', 'video', 'canvas', 'svg', 'iframe', 'object', 'embed',
            'nav', 'menu', 'aside'
        ];

        elementsToRemove.forEach(selector => {
            const elements = contentClone.querySelectorAll(selector);
            elements.forEach(el => {
                if (!el.hasAttribute('data-tts-include')) {
                    el.remove();
                }
            });
        });

        // 获取纯文本内容
        const fullText = contentClone.textContent || '';

        // 使用正则表达式分割句子
        const sentenceRegex = /[^。！？；，、.!?;,\n]+[。！？；，、.!?;,\n]*/g;
        const rawSentences = fullText.match(sentenceRegex) || [];

        // 过滤句子
        const filteredSentences = rawSentences
            .map(s => s.trim())
            .filter(s => {
                if (s.length < 3) return false;
                if (/^\d+$/.test(s)) return false;
                if (s.length > 500) return false;
                if (/^[{}[\]()<>]+$/.test(s)) return false;
                if (/^[=+*/\\|~^]+$/.test(s)) return false;

                // 检查是否包含代码片段
                const codePatterns = [
                    /function\s*\(/, /=>/, /\.\w+\(/, /\w+\.prototype/,
                    /var\s+\w+/, /let\s+\w+/, /const\s+\w+/,
                    /if\s*\(/, /for\s*\(/, /while\s*\(/,
                    /<\w+>/, /<\/\w+>/, /&[a-z]+;/,
                    /\w+:\s*\d+px/, /rgb\(/, /#[\da-f]{3,6}/,
                    /import\s+.*from/, /export\s+(default\s+)?\w+/
                ];

                for (const pattern of codePatterns) {
                    if (pattern.test(s)) {
                        return false;
                    }
                }

                return true;
            })
            .map(s => s.replace(/\s+/g, ' ').trim());

        return filteredSentences;
    };

    // 开始朗读
    const startReading = () => {
        if (isReading && !isPaused) return;

        if (isReading && isPaused) {
            resumeReading();
            return;
        }

        // 提取句子
        const extractedSentences = extractSentences();
        if (extractedSentences.length === 0) {
            alert('无法提取文章内容进行朗读');
            return;
        }

        setSentences(extractedSentences);
        setCurrentSentenceIndex(0);
        setProgress(0);
        setIsReading(true);
        setIsPaused(false);

        readCurrentSentence(extractedSentences, 0);
    };

    // 朗读当前句子
    const readCurrentSentence = (sentencesArray: string[], index: number) => {
        if (index >= sentencesArray.length) {
            setProgress(100);
            stopReading();
            return;
        }

        const sentence = sentencesArray[index];
        const utterance = new SpeechSynthesisUtterance(sentence);

        utterance.lang = 'zh-CN';
        utterance.rate = rate;
        utterance.pitch = pitch;

        // 设置选定的语音
        const selectedVoiceObj = voices.find(v => v.name === selectedVoice);
        if (selectedVoiceObj) {
            utterance.voice = selectedVoiceObj;
        }

        utterance.onend = () => {
            if (isReading && !isPaused) {
                setTimeout(() => {
                    const nextIndex = index + 1;
                    setCurrentSentenceIndex(nextIndex);
                    setProgress(Math.round((nextIndex / sentencesArray.length) * 100));
                    readCurrentSentence(sentencesArray, nextIndex);
                }, 300);
            }
        };

        utterance.onerror = (event) => {
            console.error('语音合成错误:', event);
            const nextIndex = index + 1;
            setCurrentSentenceIndex(nextIndex);
            setProgress(Math.round((nextIndex / sentencesArray.length) * 100));
            readCurrentSentence(sentencesArray, nextIndex);
        };

        utteranceRef.current = utterance;
        synthRef.current?.speak(utterance);
    };

    // 暂停朗读
    const pauseReading = () => {
        if (isReading && !isPaused) {
            synthRef.current?.pause();
            setIsPaused(true);
        }
    };

    // 恢复朗读
    const resumeReading = () => {
        if (isReading && isPaused) {
            synthRef.current?.resume();
            setIsPaused(false);
        }
    };

    // 停止朗读
    const stopReading = () => {
        synthRef.current?.cancel();
        setIsReading(false);
        setIsPaused(false);
        setCurrentSentenceIndex(0);
        setProgress(0);
    };

    // 上一句
    const goToPreviousSentence = () => {
        if (currentSentenceIndex > 0) {
            synthRef.current?.cancel();
            const newIndex = currentSentenceIndex - 1;
            setCurrentSentenceIndex(newIndex);
            setProgress(Math.round((newIndex / sentences.length) * 100));
            readCurrentSentence(sentences, newIndex);
        }
    };

    // 下一句
    const goToNextSentence = () => {
        if (currentSentenceIndex < sentences.length - 1) {
            synthRef.current?.cancel();
            const newIndex = currentSentenceIndex + 1;
            setCurrentSentenceIndex(newIndex);
            setProgress(Math.round((newIndex / sentences.length) * 100));
            readCurrentSentence(sentences, newIndex);
        }
    };

    // 更新语音设置
    const handleVoiceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setSelectedVoice(e.target.value);
    };

    const handleRateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newRate = parseFloat(e.target.value);
        setRate(newRate);
        // 如果正在朗读，更新当前语音
        if (utteranceRef.current && isReading) {
            utteranceRef.current.rate = newRate;
        }
    };

    const handlePitchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newPitch = parseFloat(e.target.value);
        setPitch(newPitch);
        // 如果正在朗读，更新当前语音
        if (utteranceRef.current && isReading) {
            utteranceRef.current.pitch = newPitch;
        }
    };

    const handleAutoScrollChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAutoScroll(e.target.checked);
    };

    const handleFilterChange = (filterType: keyof typeof filterConfig) => {
        setFilterConfig(prev => ({
            ...prev,
            [filterType]: !prev[filterType]
        }));
    };

    // 重置设置
    const resetSettings = () => {
        setRate(1.0);
        setPitch(1.0);
        setAutoScroll(true);

        // 重置过滤配置
        setFilterConfig({
            filterCode: true,
            filterScripts: true,
            filterHtmlTags: false,
            filterSpecialChars: false
        });

        // 重置语音为中文
        const chineseVoice = voices.find(v => v.lang.startsWith('zh'));
        if (chineseVoice) {
            setSelectedVoice(chineseVoice.name);
        } else if (voices.length > 0) {
            setSelectedVoice(voices[0].name);
        }
    };

    // 渲染固定控制面板（右下角）
    const FixedReadingControls = () => (
        <div
            className={`fixed bottom-[20px] right-[20px] bg-white dark:bg-gray-800 rounded-lg p-4 shadow-[0_2px_20px_rgba(0,0,0,0.15)] z-50 transition-all duration-300 min-w-[300px] ${isReading ? 'block' : 'hidden'}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                    <i className="fas fa-volume-up text-blue-600 mr-2"></i>
                    <span className="font-medium text-gray-800 dark:text-gray-200">正在朗读中...</span>
                </div>
                <button
                    onClick={stopReading}
                    className="text-gray-400 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-200"
                >
                    <i className="fas fa-times"></i>
                </button>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
                <button
                    onClick={isPaused ? resumeReading : pauseReading}
                    className={`px-3 py-1.5 rounded-md flex items-center ${
                        isPaused
                            ? 'bg-green-500 hover:bg-green-600'
                            : 'bg-yellow-500 hover:bg-yellow-600'
                    } text-white transition-colors`}
                >
                    <i className={`fas ${isPaused ? 'fa-play' : 'fa-pause'} mr-1`}></i>
                    <span>{isPaused ? '继续' : '暂停'}</span>
                </button>
                <button
                    onClick={goToPreviousSentence}
                    disabled={currentSentenceIndex <= 0}
                    className={`px-3 py-1.5 rounded-md flex items-center ${
                        currentSentenceIndex <= 0
                            ? 'bg-gray-300 cursor-not-allowed'
                            : 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500'
                    } text-gray-800 dark:text-gray-200 transition-colors`}
                >
                    <i className="fas fa-chevron-left mr-1"></i>
                    <span>上一句</span>
                </button>
                <button
                    onClick={goToNextSentence}
                    disabled={currentSentenceIndex >= sentences.length - 1}
                    className={`px-3 py-1.5 rounded-md flex items-center ${
                        currentSentenceIndex >= sentences.length - 1
                            ? 'bg-gray-300 cursor-not-allowed'
                            : 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500'
                    } text-gray-800 dark:text-gray-200 transition-colors`}
                >
                    <span>下一句</span>
                    <i className="fas fa-chevron-right ml-1"></i>
                </button>
            </div>

            <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600 dark:text-gray-400">
          速度: {rate.toFixed(1)}x
        </span>
                <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.1"
                    value={rate}
                    onChange={handleRateChange}
                    className="w-24 ml-2"
                />
            </div>
        </div>
    );

    return (
        <div
            className="min-h-screen bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 dark:text-white py-8">
            <div className="container mx-auto px-4 max-w-6xl">
                <div className="lg:grid lg:grid-cols-3 lg:gap-8">
                    {/* 文章主体 */}
                    <div className="lg:col-span-2">
                        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
                            {article.cover_image && (
                                <div className="h-64 overflow-hidden">
                                    <img
                                        src={article.cover_image}
                                        alt={article.title}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            )}

                            <div className="p-8">
                                <div className="mb-6">
                  <span
                      className="inline-block px-3 py-1 text-sm font-semibold text-blue-600 bg-blue-100 rounded-full dark:bg-blue-900 dark:text-blue-300">
                    {article.category_name || `分类${article.category_id || '未分类'}`}
                  </span>
                                </div>

                                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                                    {article.title}
                                </h1>

                                <div
                                    className="flex flex-wrap items-center text-gray-500 dark:text-gray-400 mb-6 text-sm">
                                    <span>作者: {author?.username || '未知'}</span>
                                    <span className="mx-2">•</span>
                                    <span>分类: {article.category_name || `分类${article.category_id || '未分类'}`}</span>
                                    <span className="mx-2">•</span>
                                    <span>{new Date(article.created_at).toLocaleString()}</span>
                                    <span className="mx-2">•</span>
                                    <span>阅读量: {article.views}</span>
                                    <span className="mx-2">•</span>
                                    <span>点赞: {likes}</span>
                                </div>

                                <div className="prose prose-gray dark:prose-invert max-w-none">
                                    <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        {article.excerpt || '暂无摘要'}
                                    </p>

                                    {/* 无障碍阅读工具栏 - 在文章内容上方 */}
                                    <div
                                        className="flex flex-wrap items-center justify-between mb-6 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 rounded-lg">
                                        <div className="flex items-center mb-2 sm:mb-0">
                                            <i className="fas fa-universal-access text-xl text-blue-600 dark:text-blue-400 mr-2"></i>
                                            <span
                                                className="font-medium text-gray-800 dark:text-gray-200">无障碍阅读</span>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                onClick={startReading}
                                                disabled={isReading && !isPaused}
                                                className={`px-3 py-1.5 ${isReading && !isPaused ? 'bg-gray-300' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-md flex items-center transition-colors`}
                                            >
                                                <i className="fas fa-play mr-1"></i>
                                                <span>{isReading && !isPaused ? '朗读中...' : '开始朗读'}</span>
                                            </button>
                                            <button
                                                onClick={isPaused ? resumeReading : pauseReading}
                                                disabled={!isReading}
                                                className={`px-3 py-1.5 ${!isReading ? 'bg-gray-300' : isPaused ? 'bg-green-500 hover:bg-green-600' : 'bg-yellow-500 hover:bg-yellow-600'} text-white rounded-md flex items-center transition-colors`}
                                            >
                                                <i className={`fas ${isPaused ? 'fa-play' : 'fa-pause'} mr-1`}></i>
                                                <span>{isPaused ? '继续' : '暂停'}</span>
                                            </button>
                                            <button
                                                onClick={stopReading}
                                                disabled={!isReading}
                                                className={`px-3 py-1.5 ${!isReading ? 'bg-gray-300' : 'bg-red-500 hover:bg-red-600'} text-white rounded-md flex items-center transition-colors`}
                                            >
                                                <i className="fas fa-stop mr-1"></i>
                                                <span>停止</span>
                                            </button>
                                            <button
                                                onClick={() => setShowAccessibilityControls(!showAccessibilityControls)}
                                                className="px-3 py-1.5 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-md flex items-center transition-colors"
                                            >
                                                <i className="fas fa-cog mr-1"></i>
                                                <span>设置</span>
                                            </button>
                                        </div>
                                    </div>

                                    {/* 阅读进度条 */}
                                    <div className="mb-4">
                                        <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                                            <div
                                                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                                                style={{width: `${progress}%`}}
                                            ></div>
                                        </div>
                                        <div className="text-right text-sm text-gray-600 dark:text-gray-400 mt-1">
                                            {sentences.length > 0 ? `${currentSentenceIndex + 1}/${sentences.length}` : '0/0'} ({progress}%)
                                        </div>
                                    </div>
                                    {  /* 无障碍阅读控制面板 */}
                                    {showAccessibilityControls && (
                                        <div
                                            className="mt-6 p-4 bg-white dark:bg-gray-700 rounded-lg shadow border border-gray-200 dark:border-gray-600">
                                            <h3 className="font-bold text-lg mb-4 text-gray-900 dark:text-white flex items-center">
                                                <i className="fas fa-sliders-h mr-2"></i>
                                                无障碍阅读设置
                                            </h3>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                {/* 语音设置区块 */}
                                                <div
                                                    className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                                                    <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center">
                                                        <i className="fas fa-volume-up mr-2 text-blue-500"></i>
                                                        语音设置
                                                    </h4>

                                                    <div className="space-y-4">
                                                        <div>
                                                            <label
                                                                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">语音选择</label>
                                                            <select
                                                                value={selectedVoice}
                                                                onChange={handleVoiceChange}
                                                                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded dark:bg-gray-800 dark:text-white"
                                                            >
                                                                {voices.map((voice, index) => (
                                                                    <option key={index} value={voice.name}>
                                                                        {`${voice.name} (${voice.lang})`}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        <div>
                                                            <label
                                                                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                                朗读速度: {rate.toFixed(1)}x
                                                            </label>
                                                            <input
                                                                type="range"
                                                                min="0.5"
                                                                max="2"
                                                                step="0.1"
                                                                value={rate}
                                                                onChange={handleRateChange}
                                                                className="w-full"
                                                            />
                                                        </div>

                                                        <div>
                                                            <label
                                                                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                                音调调整: {pitch.toFixed(1)}
                                                            </label>
                                                            <input
                                                                type="range"
                                                                min="0.5"
                                                                max="2"
                                                                step="0.1"
                                                                value={pitch}
                                                                onChange={handlePitchChange}
                                                                className="w-full"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* 内容过滤设置区块 */}
                                                <div
                                                    className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                                                    <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center">
                                                        <i className="fas fa-filter mr-2 text-green-500"></i>
                                                        内容过滤设置
                                                    </h4>

                                                    <div className="space-y-3">
                                                        <label className="flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={filterConfig.filterCode}
                                                                onChange={() => handleFilterChange('filterCode')}
                                                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                                                            />
                                                            <span
                                                                className="text-sm text-gray-700 dark:text-gray-300">过滤代码块</span>
                                                        </label>

                                                        <label className="flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={filterConfig.filterScripts}
                                                                onChange={() => handleFilterChange('filterScripts')}
                                                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                                                            />
                                                            <span
                                                                className="text-sm text-gray-700 dark:text-gray-300">过滤脚本和样式</span>
                                                        </label>

                                                        <label className="flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={filterConfig.filterHtmlTags}
                                                                onChange={() => handleFilterChange('filterHtmlTags')}
                                                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                                                            />
                                                            <span
                                                                className="text-sm text-gray-700 dark:text-gray-300">过滤HTML标签</span>
                                                        </label>

                                                        <label className="flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={filterConfig.filterSpecialChars}
                                                                onChange={() => handleFilterChange('filterSpecialChars')}
                                                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                                                            />
                                                            <span
                                                                className="text-sm text-gray-700 dark:text-gray-300">过滤特殊字符</span>
                                                        </label>
                                                    </div>
                                                </div>

                                                {/* 其他设置区块 */}
                                                <div
                                                    className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 md:col-span-2">
                                                    <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center">
                                                        <i className="fas fa-cogs mr-2 text-purple-500"></i>
                                                        其他设置
                                                    </h4>

                                                    <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                                                        <label className="flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={autoScroll}
                                                                onChange={handleAutoScrollChange}
                                                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                                                            />
                                                            <span
                                                                className="text-sm text-gray-700 dark:text-gray-300">自动滚动</span>
                                                        </label>

                                                        <div className="flex flex-1 gap-2">
                                                            <button
                                                                onClick={goToPreviousSentence}
                                                                disabled={currentSentenceIndex <= 0 || sentences.length === 0}
                                                                className={`px-4 py-2 rounded-md flex-1 ${
                                                                    currentSentenceIndex <= 0 || sentences.length === 0
                                                                        ? 'bg-gray-300 cursor-not-allowed'
                                                                        : 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500'
                                                                }`}
                                                            >
                                                                <i className="fas fa-chevron-left mr-1"></i>上一句
                                                            </button>
                                                            <span
                                                                className="px-4 py-2 text-gray-700 dark:text-gray-300 flex items-center justify-center min-w-[80px]">
                              {sentences.length > 0 ? `${currentSentenceIndex + 1}/${sentences.length}` : '0/0'}
                            </span>
                                                            <button
                                                                onClick={goToNextSentence}
                                                                disabled={currentSentenceIndex >= sentences.length - 1 || sentences.length === 0}
                                                                className={`px-4 py-2 rounded-md flex-1 ${
                                                                    currentSentenceIndex >= sentences.length - 1 || sentences.length === 0
                                                                        ? 'bg-gray-300 cursor-not-allowed'
                                                                        : 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500'
                                                                }`}
                                                            >
                                                                下一句<i className="fas fa-chevron-right ml-1"></i>
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div
                                                className="flex flex-wrap justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                                                <button
                                                    onClick={() => setShowAccessibilityControls(false)}
                                                    className="px-4 py-2 bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200"
                                                >
                                                    <i className="fas fa-times mr-1"></i>关闭
                                                </button>
                                                <button
                                                    onClick={resetSettings}
                                                    className="px-4 py-2 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
                                                >
                                                    <i className="fas fa-sync-alt mr-1"></i>重置设置
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    {/* 显示完整文章内容 */}
                                    <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
                                        <div
                                            ref={contentRef}
                                            className="article-content text-gray-700 dark:text-gray-300 leading-relaxed"
                                            dangerouslySetInnerHTML={{__html: article.content || '<p>这里将显示完整文章内容...</p>'}}
                                        />
                                        
                                        {/* 调试信息 */}
                                        {process.env.NODE_ENV === 'development' && (
                                            <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded text-xs text-yellow-800 dark:text-yellow-200">
                                                <p>调试信息:</p>
                                                <p>文章ID: {article.id}</p>
                                                <p>内容长度: {article.content?.length || 0}</p>
                                                <p>内容预览: {article.content?.substring(0, 100) || '无内容'}</p>
                                            </div>
                                        )}

                                        {article.tags && article.tags.length > 0 && (
                                            <div className="mt-8">
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">标签</h3>
                                                <div className="flex flex-wrap gap-2">
                                                    {article.tags.map((tag, index) => (
                                                        <span
                                                            key={index}
                                                            className="px-3 py-1 text-sm bg-gray-100 text-gray-800 rounded-full dark:bg-gray-700 dark:text-gray-200"
                                                        >
                              #{tag}
                            </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>


                                {/* 操作按钮 */}
                                <div
                                    className="flex flex-wrap items-center justify-between border-t border-gray-200 pt-6 mt-8 gap-4">
                                    <div className="flex items-center">
                                        <button
                                            type="button"
                                            onClick={handleLike}
                                            disabled={hasLiked}
                                            className={`flex items-center ${hasLiked ? 'text-red-500' : 'text-gray-600 hover:text-red-500'} ${hasLiked ? '' : 'cursor-pointer'}`}
                                        >
                                            <i className={`far ${hasLiked ? 'fa-heart text-red-500' : 'fa-heart text-xl mr-1'}`}></i>
                                            <span>{likes}</span>
                                        </button>
                                    </div>
                                    <div className="flex flex-wrap gap-4">
                                        {/* 多语言切换 */}
                                        <div className="relative group">
                                            <button className="flex items-center text-gray-600 hover:text-primary">
                                                <i className="fas fa-language mr-1"></i>
                                                语言
                                            </button>
                                            <div
                                                className="absolute right-0 bottom-full mb-2 w-48 shadow-lg rounded-md py-1 hidden group-hover:block z-10 bg-white dark:bg-gray-700">
                                                {i18n_versions.length > 0 ? (
                                                    <>
                                                        {i18n_versions.map((version: {
                                                            language_code: string;
                                                            title: string
                                                        }, index: number) => (
                                                            <a
                                                                key={index}
                                                                href={`/blog/${article.slug}?lang=${version.language_code}`}
                                                                className="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-600"
                                                            >
                                                                {version.language_code} - {version.title}
                                                            </a>
                                                        ))}
                                                    </>
                                                ) : (
                                                    <p className="block px-4 py-2 text-gray-500">暂无翻译</p>
                                                )}
                                                <Link
                                                    href={`/contribute?aid=${article.id}`}
                                                    className="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-600 border-t border-gray-200 dark:border-gray-600"
                                                >
                                                    贡献翻译
                                                </Link>
                                            </div>
                                        </div>

                                        {/* 分享按钮 */}
                                        <button
                                            className="flex items-center text-gray-600 hover:text-green-500"
                                            onClick={() => {
                                                if (navigator.share) {
                                                    navigator.share({
                                                        title: article.title,
                                                        url: window.location.href
                                                    }).catch(console.error);
                                                } else {
                                                    navigator.clipboard.writeText(window.location.href);
                                                    alert('链接已复制到剪贴板');
                                                }
                                            }}
                                        >
                                            <i className="fas fa-share-alt mr-1"></i>
                                            分享
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 侧边栏 */}
                    <div className="mt-8 lg:mt-0">
                        {/* 作者信息 */}
                        {author && (
                            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-6">
                                <div className="flex items-center mb-4">
                                    <img
                                        src={`/api/avatar/${author.id}`}
                                        alt={author.username}
                                        className="w-16 h-16 rounded-full mr-4"
                                    />
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">{author.username}</h3>
                                        <p className="text-gray-600 text-sm dark:text-gray-400">暂无简介</p>
                                    </div>
                                </div>
                                <div className="flex">
                                    <Link
                                        href={`/user/${String(author.id)}`}
                                        className="flex-grow text-center py-2 text-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                                    >
                                        更多文章
                                    </Link>
                                </div>
                            </div>
                        )}

                        {/* 广告位 */}
                        <div
                            className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 border border-blue-200 dark:border-blue-700 rounded-lg p-6 text-center">
                            <h4 className="font-bold text-gray-900 dark:text-white mb-2">加入我们的社区</h4>
                            <p className="text-gray-600 text-sm mb-4 dark:text-gray-300">获取最新技术文章和独家资源</p>
                            <button
                                className="px-4 py-2 bg-gradient-to-r from-primary to-indigo-600 text-white rounded-md hover:opacity-90">
                                立即订阅
                            </button>
                        </div>
                    </div>
                </div>

                <div className="mt-8 text-center">
                    <Link
                        href="/"
                        className="inline-block px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                        返回首页
                    </Link>
                </div>
            </div>

            {/* 固定朗读控制面板 - 位于页面右下角（与原模板一致） */}
            <FixedReadingControls/>
            
            {/* 可拖动悬浮目录 */}
            <DraggableToc />
        </div>
    );
};

export default ArticleDetailClient;