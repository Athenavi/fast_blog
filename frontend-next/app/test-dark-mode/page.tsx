/**
 * 深色模式测试页面
 * 用于验证深色模式是否正确应用到所有组件
 */

'use client';

import React from 'react';
import {useDarkMode} from '@/lib/dark-mode-manager';

export default function DarkModeTestPage() {
    const {theme, toggleTheme, setTheme} = useDarkMode();

    return (
        <div className="min-h-screen p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold mb-8 text-gray-900 dark:text-white">
                    深色模式测试页面
                </h1>

                <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                    <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
                        当前主题: {theme === 'dark' ? '深色模式' : '浅色模式'}
                    </h2>

                    <div className="flex gap-4 mb-6">
                        <button
                            onClick={() => setTheme('light')}
                            className={`px-4 py-2 rounded ${
                                theme === 'light'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                            }`}
                        >
                            浅色模式
                        </button>
                        <button
                            onClick={() => setTheme('dark')}
                            className={`px-4 py-2 rounded ${
                                theme === 'dark'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                            }`}
                        >
                            深色模式
                        </button>
                        <button
                            onClick={toggleTheme}
                            className="px-4 py-2 bg-green-600 text-white rounded"
                        >
                            切换主题
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* 卡片测试 */}
                    <div
                        className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-medium mb-3 text-gray-900 dark:text-white">卡片组件测试</h3>
                        <p className="text-gray-600 dark:text-gray-300">
                            这是一个卡片组件，应该在深色模式下有适当的背景和文字颜色。
                        </p>
                    </div>

                    {/* 按钮测试 */}
                    <div className="p-6 bg-gray-50 dark:bg-gray-900 rounded-lg shadow-md">
                        <h3 className="text-lg font-medium mb-3 text-gray-900 dark:text-white">按钮样式测试</h3>
                        <div className="flex flex-wrap gap-2">
                            <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                                主要按钮
                            </button>
                            <button
                                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
                                次要按钮
                            </button>
                            <button
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                                边框按钮
                            </button>
                        </div>
                    </div>

                    {/* 文字颜色测试 */}
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                        <h3 className="text-lg font-medium mb-3 text-gray-900 dark:text-white">文字颜色测试</h3>
                        <div className="space-y-2">
                            <p className="text-gray-900 dark:text-white">主要文字 (gray-900)</p>
                            <p className="text-gray-700 dark:text-gray-300">次要文字 (gray-700)</p>
                            <p className="text-gray-500 dark:text-gray-400">辅助文字 (gray-500)</p>
                            <p className="text-blue-600 dark:text-blue-400">链接文字 (blue-600)</p>
                        </div>
                    </div>

                    {/* 表单元素测试 */}
                    <div className="p-6 bg-gray-50 dark:bg-gray-900 rounded-lg shadow-md">
                        <h3 className="text-lg font-medium mb-3 text-gray-900 dark:text-white">表单元素测试</h3>
                        <div className="space-y-3">
                            <input
                                type="text"
                                placeholder="输入框测试"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                            <select
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
                                <option>选择框测试</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div
                    className="mt-8 p-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                    <h3 className="text-lg font-medium mb-2 text-yellow-800 dark:text-yellow-200">测试说明</h3>
                    <ul className="list-disc list-inside text-yellow-700 dark:text-yellow-300 space-y-1">
                        <li>切换主题时，所有元素的颜色应该正确变化</li>
                        <li>深色模式下，背景应该是深色的，文字应该是浅色的</li>
                        <li>按钮、卡片、表单等组件都应该有适当的深色模式样式</li>
                        <li>检查是否有遗漏的元素没有适配深色模式</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}