const AboutPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="container mx-auto px-4 max-w-3xl">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">关于我们</h1>
          
          <div className="prose prose-gray dark:prose-invert max-w-none">
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              欢迎来到FastBlog，这里有丰富的技术文章和生活分享。
            </p>
            
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              我们的平台致力于为用户提供高质量的内容创作和阅读体验。
              无论您是想分享知识、记录生活，还是寻找有价值的信息，
              FastBlog都是您的理想选择。
            </p>
            
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mt-8 mb-4">我们的使命</h2>
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              通过技术手段连接内容创作者与读者，打造一个开放、包容、高质量的知识分享社区。
            </p>
            
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mt-8 mb-4">联系我们</h2>
            <p className="text-gray-700 dark:text-gray-300">
              如果您有任何问题或建议，请随时通过我们的社交媒体或邮箱与我们联系。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutPage;