'use client';

import React, {useState} from 'react';

const PaymentMethodsPage = () => {
  const [methods, setMethods] = useState([
    { id: 1, type: 'alipay', name: '支付宝', account: '138****8888', isDefault: true },
    { id: 2, type: 'wechat', name: '微信支付', account: 'weixin****888', isDefault: false },
    { id: 3, type: 'bank_card', name: '银行卡', account: '**** **** **** 8888', isDefault: false },
  ]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newMethod, setNewMethod] = useState({ type: '', account: '' });

  const handleAddMethod = () => {
    if (newMethod.type && newMethod.account) {
      const methodNames: Record<string, string> = {
        alipay: '支付宝',
        wechat: '微信支付',
        bank_card: '银行卡'
      };

      const newMethodObj = {
        id: methods.length + 1,
        type: newMethod.type,
        name: methodNames[newMethod.type] || newMethod.type,
        account: newMethod.account,
        isDefault: methods.length === 0 // 如果是第一个，则设为默认
      };

      setMethods([...methods, newMethodObj]);
      setNewMethod({ type: '', account: '' });
      setShowAddForm(false);
    }
  };

  const handleDeleteMethod = (id: number) => {
    if (methods.length <= 1) {
      alert('至少需要保留一种支付方式');
      return;
    }
    setMethods(methods.filter(method => method.id !== id));
  };

  const handleSetDefault = (id: number) => {
    setMethods(methods.map(method => ({
      ...method,
      isDefault: method.id === id
    })));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">支付方式管理</h1>
            <button 
              onClick={() => setShowAddForm(!showAddForm)}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition"
            >
              添加新方式
            </button>
          </div>

          {/* 添加支付方式表单 */}
          {showAddForm && (
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4 dark:text-white">添加新的支付方式</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">支付方式类型</label>
                  <select
                    value={newMethod.type}
                    onChange={(e) => setNewMethod({...newMethod, type: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-lg dark:bg-gray-600 dark:border-gray-600 dark:text-white"
                  >
                    <option value="">请选择</option>
                    <option value="alipay">支付宝</option>
                    <option value="wechat">微信支付</option>
                    <option value="bank_card">银行卡</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">账户信息</label>
                  <input
                    type="text"
                    value={newMethod.account}
                    onChange={(e) => setNewMethod({...newMethod, account: e.target.value})}
                    placeholder="请输入账户信息"
                    className="w-full p-2 border border-gray-300 rounded-lg dark:bg-gray-600 dark:border-gray-600 dark:text-white"
                  />
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={handleAddMethod}
                    className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition"
                  >
                    确认添加
                  </button>
                  <button
                    onClick={() => setShowAddForm(false)}
                    className="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition dark:bg-gray-600 dark:text-white"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 支付方式列表 */}
          <div className="space-y-4">
            {methods.map((method) => (
              <div 
                key={method.id} 
                className={`border rounded-lg p-4 flex justify-between items-center ${
                  method.isDefault 
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                    : 'border-gray-200 dark:border-gray-700'
                }`}
              >
                <div className="flex items-center">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${
                    method.type === 'alipay' ? 'bg-blue-500' :
                    method.type === 'wechat' ? 'bg-green-500' :
                    'bg-gray-500'
                  }`}>
                    {method.type === 'alipay' && (
                      <i className="fab fa-alipay text-white text-xl"></i>
                    )}
                    {method.type === 'wechat' && (
                      <i className="fab fa-weixin text-white text-xl"></i>
                    )}
                    {method.type === 'bank_card' && (
                      <i className="fas fa-credit-card text-white text-xl"></i>
                    )}
                  </div>
                  
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {method.name}
                      {method.isDefault && (
                        <span className="ml-2 bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded dark:bg-purple-900 dark:text-purple-200">
                          默认
                        </span>
                      )}
                    </div>
                    <div className="text-gray-600 dark:text-gray-400">{method.account}</div>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  {!method.isDefault && (
                    <button
                      onClick={() => handleSetDefault(method.id)}
                      className="text-sm bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 transition dark:bg-gray-600 dark:text-white"
                    >
                      设为默认
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteMethod(method.id)}
                    className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200 transition dark:bg-red-900/30 dark:text-red-400"
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
            
            {methods.length === 0 && (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <i className="fas fa-wallet text-5xl mb-4"></i>
                <p>暂无支付方式，请添加一个新的支付方式</p>
              </div>
            )}
          </div>

          {/* 提示信息 */}
          <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200 dark:bg-blue-900/20 dark:border-blue-800">
            <h3 className="font-semibold text-blue-800 dark:text-blue-300 flex items-center">
              <i className="fas fa-info-circle mr-2"></i>
              安全提示
            </h3>
            <p className="text-blue-700 dark:text-blue-400 mt-2">
              请妥善保管您的支付信息，我们采用行业标准加密技术保护您的账户安全。
              如需修改或删除支付方式，请及时操作。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentMethodsPage;