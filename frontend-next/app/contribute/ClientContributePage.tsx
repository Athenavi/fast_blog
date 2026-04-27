'use client';

import React, {useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {ContributionService} from '@/lib/api/article-service';

interface LanguageOption {
    code: string;
    name: string;
}

const ContributePage = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const aid = searchParams.get('aid'); // 文章ID

    // 步骤状态
    const [currentStep, setCurrentStep] = useState<number>(1);
    const [progress, setProgress] = useState<number>(33);

    // 表单数据
    const [formData, setFormData] = useState({
        contribute_language: '',
        contribute_title: '',
        contribute_slug: '',
        contribute_content: ''
    });

    // 状态数据
    const [validLanguageCodes, setValidLanguageCodes] = useState<string[]>([]);
    const [existingLanguages, setExistingLanguages] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>('');

    // 模拟语言选项，实际应用中应从API获取
    const languageOptions: LanguageOption[] = [
        {code: 'zh', name: '中文'},
        {code: 'en', name: 'English'},
        {code: 'ja', name: '日本語'},
        {code: 'ko', name: '한국어'},
        {code: 'fr', name: 'Français'},
        {code: 'de', name: 'Deutsch'},
        {code: 'es', name: 'Español'},
    ];

    // 初始化数据
    useEffect(() => {
        if (!aid) {
            setErrorMessage('缺少文章ID');
            setIsLoading(false);
            return;
        }

        const fetchArticleInfo = async () => {
            try {
                setIsLoading(true);

                // 获取文章贡献信息
                const response = await ContributionService.getContributionInfo(aid);

                if (response.success && response.data) {
                    // 获取语言选项（这里暂时使用静态数据，实际应用中应从API获取）
                    setValidLanguageCodes(['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es']);

                    // 如果有现有翻译，获取它们
                    // 这里需要额外的API调用来获取现有翻译，暂时使用示例数据
                    setExistingLanguages(['zh', 'en']); // 示例数据
                } else {
                    console.error('获取文章信息失败:', response.error);
                    setExistingLanguages([]); // 没有现有翻译
                }

                setIsLoading(false);
            } catch (error) {
                console.error('获取文章信息失败:', error);
                setErrorMessage('获取文章信息失败');
                setIsLoading(false);
            }
        };

        fetchArticleInfo();
    }, [aid]);

    // 更新进度条
    useEffect(() => {
        const newProgress = (currentStep / 3) * 100;
        setProgress(newProgress);
    }, [currentStep]);

    // 处理输入更改
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const {name, value} = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));

        // 如果是slug输入，实时更新预览
        if (name === 'contribute_slug') {
            setFormData(prev => ({
                ...prev,
                contribute_slug: value.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-')
            }));
        }
    };

    // 验证当前步骤
    const validateStep = (step: number): boolean => {
        if (step === 1) {
            if (!formData.contribute_language) {
                setErrorMessage('请选择翻译语言');
                return false;
            }
        } else if (step === 2) {
            if (!formData.contribute_title.trim()) {
                setErrorMessage('请输入翻译标题');
                return false;
            }
            if (!formData.contribute_slug.trim()) {
                setErrorMessage('请输入URL别名');
                return false;
            }
            if (!formData.contribute_content.trim()) {
                setErrorMessage('请输入翻译内容');
                return false;
            }
        }
        return true;
    };

    // 切换步骤
    const goToStep = (step: number) => {
        if (step > currentStep) {
            if (!validateStep(currentStep)) {
                return;
            }
        }
        setCurrentStep(step);
    };

    // 提交翻译
    const handleSubmit = async () => {
        if (!validateStep(3)) {
            return;
        }

        setIsSubmitting(true);
        try {
            // 调用后端API提交翻译
            const response = await ContributionService.submitContribution(aid!, {
                contribute_type: 'translation',
                ...formData
            });

            if (response.success && response.data) {
                setSubmitSuccess(true);
            } else {
                setErrorMessage(response.error || response.message || '提交失败');
            }
        } catch (error) {
            console.error('提交翻译失败:', error);
            setErrorMessage('网络错误，请稍后重试');
        } finally {
            setIsSubmitting(false);
        }
    };

    // 重置表单
    const resetForm = () => {
        setFormData({
            contribute_language: '',
            contribute_title: '',
            contribute_slug: '',
            contribute_content: ''
        });
        setCurrentStep(1);
        setSubmitSuccess(false);
    };

    if (isLoading) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-5xl flex justify-center items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            {/* Header */}
            <header className="bg-white shadow-sm rounded-lg p-6 mb-8">
                <h1 className="text-3xl font-bold text-gray-800">Contribute Translation</h1>
                <p className="text-gray-600 mt-2">Help translate this article to make it accessible to more readers
                    worldwide</p>
            </header>

            <div className="bg-white shadow-md rounded-lg overflow-hidden">
                {/* Progress Bar */}
                <div className="bg-gray-200 h-2 w-full">
                    <div
                        className="bg-primary h-2 transition-all duration-300"
                        id="progressBar"
                        style={{width: `${progress}%`}}
                    ></div>
                </div>

                {/* Form Steps */}
                <form className="p-6">
                    {/* Step 1: Language Selection */}
                    <div className={`${currentStep === 1 ? 'block' : 'hidden'}`} id="step1">
                        <h2 className="text-xl font-semibold text-gray-800 mb-4">1. Select Language</h2>
                        <p className="text-gray-600 mb-6">Choose the language you want to translate this article
                            into.</p>

                        <div className="mb-4">
                            <label className="block text-gray-700 text-sm font-medium mb-2"
                                   htmlFor="contribute_language">
                                Language *
                            </label>
                            <select
                                name="contribute_language"
                                id="contribute_language"
                                value={formData.contribute_language}
                                onChange={handleInputChange}
                                required
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                            >
                                <option value="">Select a language</option>
                                {languageOptions.map((lang) => (
                                    <option key={lang.code} value={lang.code}>
                                        {lang.name} ({lang.code})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {existingLanguages.length > 0 && (
                            <div className="bg-blue-50 p-4 rounded-md mb-6">
                                <h3 className="font-medium text-blue-800">Existing Translations</h3>
                                <p className="text-blue-600 text-sm mt-1">This article already has translations in these
                                    languages:</p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {existingLanguages.map((lang, index) => (
                                        <span key={index}
                                              className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                      {lang}
                    </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex justify-end">
                            <button
                                type="button"
                                onClick={() => goToStep(2)}
                                className="bg-primary text-white px-4 py-2 rounded-md hover:bg-secondary transition flex items-center"
                            >
                                Next <i className="fas fa-arrow-right ml-2"></i>
                            </button>
                        </div>
                    </div>

                    {/* Step 2: Content Translation */}
                    <div className={`${currentStep === 2 ? 'block' : 'hidden'}`} id="step2">
                        <h2 className="text-xl font-semibold text-gray-800 mb-4">2. Translate Content</h2>
                        <p className="text-gray-600 mb-6">Translate the article title and content below.</p>

                        <div className="mb-6">
                            <label className="block text-gray-700 text-sm font-medium mb-2" htmlFor="contribute_title">
                                Article Title *
                            </label>
                            <input
                                type="text"
                                name="contribute_title"
                                id="contribute_title"
                                value={formData.contribute_title}
                                onChange={handleInputChange}
                                required
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                placeholder="Translated article title"
                            />
                        </div>

                        <div className="mb-6">
                            <label className="block text-gray-700 text-sm font-medium mb-2" htmlFor="contribute_slug">
                                URL Slug *
                            </label>
                            <input
                                type="text"
                                name="contribute_slug"
                                id="contribute_slug"
                                value={formData.contribute_slug}
                                onChange={handleInputChange}
                                required
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                placeholder="translated-article-title"
                            />
                            <p className="text-gray-500 text-xs mt-1">This will be used in the article URL. Only
                                letters, numbers, and hyphens are allowed.</p>
                            <div className="mt-2">
                                <span className="text-gray-700 text-sm">Preview: </span>
                                <span id="slugPreview" className="text-sm">
                  /{aid}.html/{formData.contribute_language}/{formData.contribute_slug || 'your-slug-will-appear-here'}
                </span>
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-gray-700 text-sm font-medium mb-2">
                                Article Content *
                            </label>
                            <div className="markdown-toolbar bg-gray-50 border border-gray-300 rounded-t-md p-2">
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-bold"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-italic"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-heading"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-link"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-quote-right"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-code"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-image"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-list-ul"></i></button>
                                <button type="button" className="p-1 m-1 rounded border border-gray-300 bg-white"><i
                                    className="fas fa-list-ol"></i></button>
                            </div>
                            <textarea
                                name="contribute_content"
                                id="contribute_content"
                                value={formData.contribute_content}
                                onChange={handleInputChange}
                                required
                                className="w-full min-h-[300px] border border-gray-300 border-t-0 rounded-b-md p-4 font-mono focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                placeholder="Write your translation in Markdown format"
                            />
                        </div>

                        <div className="flex justify-between">
                            <button
                                type="button"
                                onClick={() => goToStep(1)}
                                className="text-gray-600 px-4 py-2 rounded-md hover:bg-gray-100 transition flex items-center"
                            >
                                <i className="fas fa-arrow-left mr-2"></i> Back
                            </button>
                            <button
                                type="button"
                                onClick={() => goToStep(3)}
                                className="bg-primary text-white px-4 py-2 rounded-md hover:bg-secondary transition flex items-center"
                            >
                                Next <i className="fas fa-arrow-right ml-2"></i>
                            </button>
                        </div>
                    </div>

                    {/* Step 3: Review & Submit */}
                    <div className={`${currentStep === 3 ? 'block' : 'hidden'}`} id="step3">
                        <h2 className="text-xl font-semibold text-gray-800 mb-4">3. Review & Submit</h2>
                        <p className="text-gray-600 mb-6">Review your translation before submitting.</p>

                        <div className="bg-gray-50 p-4 rounded-md mb-6">
                            <h3 className="font-medium text-gray-800">Translation Details</h3>
                            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-gray-600">Language</p>
                                    <p className="font-medium">{languageOptions.find(l => l.code === formData.contribute_language)?.name || formData.contribute_language}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Title</p>
                                    <p className="font-medium">{formData.contribute_title}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">URL Slug</p>
                                    <p className="font-medium">{formData.contribute_slug}</p>
                                </div>
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-gray-700 text-sm font-medium mb-2">
                                Content Preview
                            </label>
                            <div
                                className="markdown-preview bg-white border border-gray-300 p-4 rounded-md min-h-[300px]">
                                {formData.contribute_content ? (
                                    <div
                                        dangerouslySetInnerHTML={{__html: formData.contribute_content.replace(/\n/g, '<br>')}}/>
                                ) : (
                                    <p className="text-gray-500">Your content will be previewed here...</p>
                                )}
                            </div>
                        </div>

                        <div className="flex justify-between">
                            <button
                                type="button"
                                onClick={() => goToStep(2)}
                                className="text-gray-600 px-4 py-2 rounded-md hover:bg-gray-100 transition flex items-center"
                            >
                                <i className="fas fa-arrow-left mr-2"></i> Back
                            </button>
                            <button
                                type="button"
                                onClick={handleSubmit}
                                disabled={isSubmitting}
                                className={`${
                                    isSubmitting ? 'bg-gray-400' : 'bg-green-600 hover:bg-green-700'
                                } text-white px-4 py-2 rounded-md transition flex items-center`}
                            >
                                {isSubmitting ? (
                                    <>
                                        <i className="fas fa-spinner fa-spin mr-2"></i> Submitting...
                                    </>
                                ) : (
                                    <>
                                        <i className="fas fa-paper-plane mr-2"></i> Submit Translation
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </form>
            </div>

            {/* Success Modal */}
            {submitSuccess && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                        <div className="text-center">
                            <div
                                className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i className="fas fa-check text-green-600 text-2xl"></i>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-800 mb-2">Success!</h3>
                            <p className="text-gray-600 mb-4">Your translation has been submitted successfully.</p>
                            <button
                                onClick={() => {
                                    resetForm();
                                    router.push('/');
                                }}
                                className="bg-primary text-white px-4 py-2 rounded-md hover:bg-secondary transition"
                            >
                                Continue
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Error Modal */}
            {errorMessage && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                        <div className="text-center">
                            <div
                                className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i className="fas fa-exclamation-triangle text-red-600 text-2xl"></i>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-800 mb-2">Error!</h3>
                            <p className="text-gray-600 mb-4">{errorMessage}</p>
                            <button
                                onClick={() => setErrorMessage('')}
                                className="bg-primary text-white px-4 py-2 rounded-md hover:bg-secondary transition"
                            >
                                Try Again
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ContributePage;