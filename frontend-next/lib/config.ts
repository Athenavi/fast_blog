// 运行时配置加载器
// 优先从运行时配置文件加载，如果没有则使用默认配置

let runtimeApiConfig: { API_BASE_URL: string; API_PREFIX: string } | null = null;

// 异步加载运行时配置
export const loadRuntimeConfig = async (): Promise<{ API_BASE_URL: string; API_PREFIX: string }> => {
    if (runtimeApiConfig) {
        return runtimeApiConfig;
    }

    try {
        // 在浏览器环境中尝试加载运行时配置
        if (typeof window !== 'undefined') {
            // 使用完整的 URL 路径
            const configUrl = `${window.location.origin}/config.js`;
            const response = await fetch(configUrl);
            if (response.ok) {
                const configText = await response.text();
                // 动态执行配置脚本
                const configModule = eval(configText + '; runtimeConfig');
                runtimeApiConfig = {
                    API_BASE_URL: configModule.API_BASE_URL,
                    API_PREFIX: configModule.API_PREFIX || '/api/v1'
                };
                console.log('✅ 已加载运行时 API 配置:', runtimeApiConfig.API_BASE_URL);
                return runtimeApiConfig;
            }
        }
    } catch (error) {
        console.warn('⚠️ 未找到运行时配置，使用默认配置');
    }

    // 默认配置（构建时配置）
    runtimeApiConfig = {
        API_BASE_URL: 'http://localhost:9421',
        API_PREFIX: '/api/v1'  // 使用 FastAPI/Django 共享的 API 路由
    };

    return runtimeApiConfig;
};

// 同步获取配置（如果已加载）
export const getConfig = (): { API_BASE_URL: string; API_PREFIX: string } => {
    return runtimeApiConfig || {
        API_BASE_URL: 'http://localhost:9421',
        API_PREFIX: '/api/v1'  // 使用 FastAPI/Django 共享的 API 路由
    };
};
