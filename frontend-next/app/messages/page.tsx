'use client';

import React, {useEffect, useState} from 'react';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient} from '@/lib/api';

interface Message {
  id: number;
  title: string;
  content?: string;
  sender?: string;
  recipient?: string;
  date: string;
  type: string;
  read: boolean;
  avatar?: string;
}

const MessagesPage = () => {
  const [activeTab, setActiveTab] = useState('inbox');
  const [inboxMessages, setInboxMessages] = useState<Message[]>([]);
  const [sentMessages, setSentMessages] = useState<Message[]>([]);
  const [notifications, setNotifications] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  // 加载消息数据
  useEffect(() => {
    const loadMessages = async () => {
      try {
        setLoading(true);
        // 调用API获取消息数据
        const response = await apiClient.get('/notifications/');

        if (response.success && response.data) {
          // 根据API返回的数据格式，目前API主要返回通知
          setNotifications(Array.isArray(response.data) ? response.data : []);

          // 对于收件箱和已发送消息，暂时设置为空数组
          // 在实际实现中，这里应该有相应的API来获取不同类型的消息
          setInboxMessages([]);
          setSentMessages([]);
        }
      } catch (error) {
        console.error('加载消息时出错:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMessages();
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
  };

  const getMessageType = (type: string) => {
    switch (type) {
      case 'welcome':
      case 'system':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'comment':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'feedback':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  const getMessageTypeName = (type: string) => {
    switch (type) {
      case 'welcome': return '欢迎消息';
      case 'comment': return '评论提醒';
      case 'system': return '系统消息';
      case 'feedback': return '反馈消息';
      default: return type;
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'follow': return '👥';
      case 'publish': return '📝';
      case 'comment': return '💬';
      case 'like': return '❤️';
      default: return '🔔';
    }
  };

  const refreshMessages = async () => {
    try {
      setLoading(true);
      // 调用API获取消息数据
      const response = await apiClient.get('/notifications/');

      if (response.success && response.data) {
        // 根据API返回的数据格式，目前API主要返回通知
        setNotifications(Array.isArray(response.data) ? response.data : []);

        // 对于收件箱和已发送消息，暂时设置为空数组
        setInboxMessages([]);
        setSentMessages([]);
      }
    } catch (error) {
      console.error('刷新消息时出错:', error);
    } finally {
      setLoading(false);
    }
  };

  const viewMessage = (id: number) => {
    console.log(`查看消息 ${id}`);
  };

  const viewNotification = (id: number) => {
    console.log(`查看通知 ${id}`);
  };

  const markAsRead = async (id: number) => {
    try {
      const response = await apiClient.patch(`/notifications/${id}/read`);

      if (response.success) {
        // 更新本地状态
        setInboxMessages(messages =>
          messages.map(msg =>
            msg.id === id ? {...msg, read: true} : msg
          )
        );

        setNotifications(notifications =>
          notifications.map(notif =>
            notif.id === id ? {...notif, read: true} : notif
          )
        );
      } else {
        console.error('标记为已读失败:', response.error);
      }
    } catch (error) {
      console.error('标记为已读时出错:', error);
    }
  };

  const deleteMessage = async (id: number) => {
    if (confirm('确定要删除这条消息吗？')) {
      try {
        const response = await apiClient.delete(`/notifications/${id}`);

        if (response.success) {
          // 更新本地状态
          setInboxMessages(messages => messages.filter(msg => msg.id !== id));
          setSentMessages(messages => messages.filter(msg => msg.id !== id));
          setNotifications(notifications => notifications.filter(notif => notif.id !== id));
        } else {
          console.error('删除消息失败:', response.error);
        }
      } catch (error) {
        console.error('删除消息时出错:', error);
      }
    }
  };

  const renderInboxTab = () => (
    <div className="space-y-4">
      {inboxMessages.length > 0 ? (
        inboxMessages.map((message) => (
          <div
            key={message.id}
            className="border rounded-lg p-4 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:hover:bg-gray-800"
          >
            <div className="flex items-start gap-4">
              <img
                src={message.avatar || 'https://via.placeholder.com/48'}
                alt="头像"
                className="w-12 h-12 rounded-full object-cover"
              />
              <div className="flex-1">
                <div className="flex justify-between">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">{message.title}</h3>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{formatDate(message.date)}</span>
                </div>
                <p className="text-gray-500 text-sm dark:text-gray-400">
                  {message.sender} • {formatDate(message.date)}
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${getMessageType(message.type)}`}>
                    {getMessageTypeName(message.type)}
                  </span>
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                    message.read 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                      : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  }`}>
                    {message.read ? '已读' : '未读'}
                  </span>
                </div>

                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => viewMessage(message.id)}
                    className="text-sm bg-blue-500 hover:bg-blue-600 text-white py-1.5 px-3 rounded"
                  >
                    查看详情
                  </button>
                  <button
                    onClick={() => markAsRead(message.id)}
                    disabled={message.read}
                    className={`text-sm py-1.5 px-3 rounded ${
                      message.read
                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed dark:bg-gray-700'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    }`}
                  >
                    标记为已读
                  </button>
                  <button
                    onClick={() => deleteMessage(message.id)}
                    className="text-sm bg-red-500 hover:bg-red-600 text-white py-1.5 px-3 rounded"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="py-12 text-center">
          <div className="text-gray-400 mb-4 dark:text-gray-500">
            <i className="fas fa-envelope-open-text text-4xl"></i>
          </div>
          <p className="text-gray-600 dark:text-gray-400">暂无消息</p>
        </div>
      )}
    </div>
  );

  const renderSentTab = () => (
    <div className="space-y-4">
      {sentMessages.length > 0 ? (
        sentMessages.map((message) => (
          <div
            key={message.id}
            className="border rounded-lg p-4 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:hover:bg-gray-800"
          >
            <div className="flex items-start gap-4">
              <img
                src={message.avatar || 'https://via.placeholder.com/48'}
                alt="头像"
                className="w-12 h-12 rounded-full object-cover"
              />
              <div className="flex-1">
                <div className="flex justify-between">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">{message.title}</h3>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{formatDate(message.date)}</span>
                </div>
                <p className="text-gray-500 text-sm dark:text-gray-400">
                  发送给 {message.recipient} • {formatDate(message.date)}
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${getMessageType(message.type)}`}>
                    {getMessageTypeName(message.type)}
                  </span>
                </div>

                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => viewMessage(message.id)}
                    className="text-sm bg-blue-500 hover:bg-blue-600 text-white py-1.5 px-3 rounded"
                  >
                    查看详情
                  </button>
                  <button
                    onClick={() => deleteMessage(message.id)}
                    className="text-sm bg-red-500 hover:bg-red-600 text-white py-1.5 px-3 rounded"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="py-12 text-center">
          <div className="text-gray-400 mb-4 dark:text-gray-500">
            <i className="fas fa-paper-plane text-4xl"></i>
          </div>
          <p className="text-gray-600 dark:text-gray-400">暂无已发送消息</p>
        </div>
      )}
    </div>
  );

  const renderNotificationsTab = () => (
    <div className="space-y-4">
      {loading ? (
        <div className="py-12 text-center">
          <p className="text-gray-600 dark:text-gray-400">加载中...</p>
        </div>
      ) : notifications.length > 0 ? (
        notifications.map((notification) => (
          <div
            key={notification.id}
            className="border rounded-lg p-4 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:hover:bg-gray-800"
          >
            <div className="flex items-start gap-4">
              <div className="text-2xl">
                {getNotificationIcon(notification.type)}
              </div>
              <div className="flex-1">
                <div className="flex justify-between">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">{notification.title}</h3>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{formatDate(notification.date)}</span>
                </div>

                {notification.content && (
                  <p className="text-gray-600 mt-2 dark:text-gray-300">
                    {notification.content}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                    notification.read 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                      : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  }`}>
                    {notification.read ? '已读' : '未读'}
                  </span>
                </div>

                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => viewNotification(notification.id)}
                    className="text-sm bg-blue-500 hover:bg-blue-600 text-white py-1.5 px-3 rounded"
                  >
                    查看详情
                  </button>
                  <button
                    onClick={() => markAsRead(notification.id)}
                    disabled={notification.read}
                    className={`text-sm py-1.5 px-3 rounded ${
                      notification.read
                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed dark:bg-gray-700'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    }`}
                  >
                    标记为已读
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="py-12 text-center">
          <div className="text-gray-400 mb-4 dark:text-gray-500">
            <i className="fas fa-bell text-4xl"></i>
          </div>
          <p className="text-gray-600 dark:text-gray-400">暂无通知</p>
        </div>
      )}
    </div>
  );

  return (
    <WithAuthProtection loadingMessage="正在加载消息...">
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-800 dark:text-white">我的消息</h1>
                <button
                  onClick={refreshMessages}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm disabled:opacity-50"
                >
                  {loading ? '刷新中...' : '刷新'}
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="border-b border-gray-200 dark:border-gray-700">
                <nav className="-mb-px flex space-x-8">
                  <button
                    onClick={() => setActiveTab('inbox')}
                    className={`py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'inbox'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                    }`}
                  >
                    收件箱
                  </button>
                  <button
                    onClick={() => setActiveTab('sent')}
                    className={`py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'sent'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                    }`}
                  >
                    已发送
                  </button>
                  <button
                    onClick={() => setActiveTab('notifications')}
                    className={`py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'notifications'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                    }`}
                  >
                    通知
                  </button>
                </nav>
              </div>

              <div className="mt-6">
                {activeTab === 'inbox' && renderInboxTab()}
                {activeTab === 'sent' && renderSentTab()}
                {activeTab === 'notifications' && renderNotificationsTab()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </WithAuthProtection>
  );
};

export default MessagesPage;