// 在浏览器控制台中运行此代码来诊断主题问题

console.log('=== 主题诊断 ===');
console.log('1. HTML 元素的 class:', document.documentElement.classList.toString());
console.log('2. localStorage theme:', localStorage.getItem('theme'));
console.log('3. body 的背景色:', getComputedStyle(document.body).backgroundColor);

// 查找 header 元素
const header = document.querySelector('header');
if (header) {
    console.log('4. Header 元素找到:', header);
    console.log('5. Header 的 class:', header.className);
    console.log('6. Header 的 style:', header.style.cssText);
    console.log('7. Header 的计算样式 - background-color:', getComputedStyle(header).backgroundColor);
    console.log('8. Header 的 data-theme 属性:', header.getAttribute('data-theme'));
} else {
    console.log('4. Header 元素未找到');
}

console.log('=== 诊断结束 ===');
