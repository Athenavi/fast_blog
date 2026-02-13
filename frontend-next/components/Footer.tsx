import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-8">
      <div className="container mx-auto px-4">
        <div className="text-center text-gray-600 dark:text-gray-400">
          <p>&copy; {new Date().getFullYear()} FastBlog. All rights reserved.</p>
          <p className="mt-2 text-sm">欢迎来到FastBlog，这里有丰富的技术文章和生活分享</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;