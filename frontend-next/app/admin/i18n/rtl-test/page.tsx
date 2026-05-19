'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, ArrowRight, CheckCircle } from 'lucide-react';

export default function RTLTestPage() {
  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">RTL语言支持测试</h1>
        <p className="text-gray-600 mt-1">测试从右到左(阿拉伯语、希伯来语)语言布局</p>
      </div>

      {/* RTL说明 */}
      <Card>
        <CardHeader>
          <CardTitle>什么是RTL?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-700">
            RTL (Right-to-Left) 是指从右到左的阅读和书写方向,主要用于:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>阿拉伯语 (Arabic)</strong> - 超过4亿使用者</li>
            <li><strong>希伯来语 (Hebrew)</strong> - 以色列官方语言</li>
            <li><strong>波斯语 (Persian/Farsi)</strong> - 伊朗官方语言</li>
            <li><strong>乌尔都语 (Urdu)</strong> - 巴基斯坦官方语言</li>
          </ul>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
            <h3 className="font-semibold text-blue-900 mb-2">示例文本:</h3>
            <p className="text-lg" dir="rtl" lang="ar">
              مرحبا بك في موقعنا الإلكتروني
            </p>
            <p className="text-sm text-gray-600 mt-2">
              (阿拉伯语: "欢迎来到我们的网站")
            </p>
            
            <p className="text-lg mt-4" dir="rtl" lang="he">
              ברוכים הבאים לאתר שלנו
            </p>
            <p className="text-sm text-gray-600 mt-2">
              (希伯来语: "欢迎来到我们的网站")
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 布局测试 */}
      <Card>
        <CardHeader>
          <CardTitle>布局翻转测试</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Flexbox方向 */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">Flexbox Row (LTR):</h3>
            <div className="flex flex-row space-x-2">
              <Badge>Item 1</Badge>
              <Badge>Item 2</Badge>
              <Badge>Item 3</Badge>
            </div>
          </div>
          
          <div>
            <h3 className="font-medium text-gray-900 mb-2">Flexbox Row (RTL):</h3>
            <div className="flex flex-row space-x-2" dir="rtl">
              <Badge>项目 1</Badge>
              <Badge>项目 2</Badge>
              <Badge>项目 3</Badge>
            </div>
          </div>

          {/* 按钮图标 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">LTR 按钮:</h3>
              <Button>
                <ArrowRight className="w-4 h-4 mr-2" />
                Next
              </Button>
            </div>
            
            <div dir="rtl">
              <h3 className="font-medium text-gray-900 mb-2">RTL 按钮:</h3>
              <Button>
                <ArrowLeft className="w-4 h-4 ml-2" />
                下一步
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 表格测试 */}
      <Card>
        <CardHeader>
          <CardTitle>表格对齐测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div dir="rtl">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-right p-2">姓名</th>
                  <th className="text-right p-2">邮箱</th>
                  <th className="text-right p-2">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="p-2">أحمد محمد</td>
                  <td className="p-2">ahmed@example.com</td>
                  <td className="p-2">
                    <Badge variant="default">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      活跃
                    </Badge>
                  </td>
                </tr>
                <tr>
                  <td className="p-2">فاطمة علي</td>
                  <td className="p-2">fatima@example.com</td>
                  <td className="p-2">
                    <Badge variant="secondary">待审核</Badge>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 表单测试 */}
      <Card>
        <CardHeader>
          <CardTitle>表单元素测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div dir="rtl" className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">用户名 / اسم المستخدم</label>
              <input 
                type="text" 
                placeholder="请输入用户名"
                className="w-full px-3 py-2 border rounded-md"
                dir="rtl"
              />
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="checkbox" id="remember" />
              <label htmlFor="remember">记住我 / تذكرني</label>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="radio" name="option" id="opt1" />
              <label htmlFor="opt1">选项一 / الخيار الأول</label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 引用块测试 */}
      <Card>
        <CardHeader>
          <CardTitle>引用块测试</CardTitle>
        </CardHeader>
        <CardContent>
          <blockquote 
            dir="rtl" 
            className="border-r-4 border-gray-300 pr-4 py-2 italic text-gray-700"
          >
            "العلم نور والجهل ظلام"
            <footer className="text-sm text-gray-500 mt-2 not-italic">
              — 阿拉伯谚语 (知识是光,无知是黑暗)
            </footer>
          </blockquote>
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>如何启用RTL?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <ol className="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>在语言切换器中选择阿拉伯语(ar)或希伯来语(he)</li>
            <li>系统会自动设置 <code className="bg-gray-100 px-2 py-1 rounded">&lt;html dir="rtl"&gt;</code></li>
            <li>CSS样式会自动应用RTL规则</li>
            <li>所有布局会水平翻转</li>
          </ol>
          
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
            <h3 className="font-semibold text-yellow-900 mb-2">注意事项:</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-yellow-800">
              <li>代码块(<code>code</code>, <code>pre</code>)保持LTR方向</li>
              <li>数字和拉丁字母在RTL文本中仍从左到右显示</li>
              <li>图标可能需要镜像翻转(使用 .icon-flip 类)</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
