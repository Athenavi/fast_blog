'use client';

import React, {useEffect, useRef, useState} from 'react';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient} from '@/lib/api';
import {FaComments, FaPaperPlane, FaPlus, FaSignOutAlt, FaUsers} from 'react-icons/fa';
import {getAccessTokenFromCookie} from "@/lib/auth-utils";

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

interface ChatGroup {
  id: number;
  name: string;
  description?: string;
  avatar?: string;
  member_count: number;
  last_message_at?: string;
}

interface ChatMessage {
  id: number;
  sender: number;
  content: string;
  message_type: string;
  created_at: string;
  is_read: boolean;
}

const MessagesPage = async () => {
  const [activeTab, setActiveTab] = useState('inbox');
  const [inboxMessages, setInboxMessages] = useState<Message[]>([]);
  const [sentMessages, setSentMessages] = useState<Message[]>([]);
  const [notifications, setNotifications] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

    // 群聊状态  const [chatGroups, setChatGroups] = useState<ChatGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<ChatGroup | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

    // 模态框状态  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [inviteLink, setInviteLink] = useState('');
  const [newMemberIds, setNewMemberIds] = useState(''); // 保留用于添加成员功能

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
        case 'welcome':
            return '欢迎消信息;
      case 'comment': return '评论提醒';
        case 'system':
            return '系统消信息;
        case 'feedback':
            return '反馈消信息;
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
        console.error('刷新消息时出错误, error);
    } finally {
      setLoading(false);
    }
  };

  // 加载群聊列表
  const loadChatGroups = async () => {
    try {
      console.log('[ChatGroup] Loading chat groups...');
      const response = await apiClient.get('/chat-groups/');
      console.log('[ChatGroup] API response:', response);
      if (response.success && response.data) {
        console.log('[ChatGroup] Groups data:', response.data.groups);
        setChatGroups(response.data.groups || []);
      } else {
        console.error('[ChatGroup] Failed to load groups:', response.error);
      }
    } catch (error) {
      console.error('加载群聊列表失败:', error);
    }
  };

  // 加载群聊消息历史
  const loadGroupMessages = async (groupId: number) => {
    try {
      const response = await apiClient.get(`/private-messages/?group=${groupId}&limit=50`);
      if (response.success && response.data) {
        setChatMessages(Array.isArray(response.data) ? response.data.reverse() : []);
      }
    } catch (error) {
      console.error('加载群聊消息失败:', error);
    }
  };

  // 连接到群聊WebSocket
  const connectToGroupChat = (groupId: number) => {
    console.log('[ChatGroup] Attempting to connect to group:', groupId);
    
    // 关闭现有连接
    if (wsRef.current) {
      console.log('[ChatGroup] Closing existing connection');
      wsRef.current.close();
    }

    // 获取token - 尝试多种方式
    let token = getAccessTokenFromCookie();

    if (!token) {
      console.error('[ChatGroup] No authentication token found');
      console.log('[ChatGroup] Available cookies:', document.cookie);
      setWsConnected(false);
      return;
    }

    // 建立WebSocket连接
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v2/ws/chat/${groupId}?token=${token}`;

    console.log('[ChatGroup] Connecting to:', wsUrl.replace(token, '***'));

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[ChatGroup] WebSocket connected successfully');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('[ChatGroup] Received message:', data);

      switch (data.type) {
        case 'new_message':
          setChatMessages(prev => [...prev, data.message]);
          scrollToBottom();
          break;
        case 'user_joined':
          console.log(`User ${data.user_id} joined the group`);
          break;
        case 'user_left':
          console.log(`User left the group`);
          break;
        case 'user_typing':
          // 可以显示“对方正在输入...'          break;
        default:
          console.log('[ChatGroup] Unknown message type:', data.type);
      }
    };

    ws.onerror = (error) => {
      console.error('[ChatGroup] WebSocket error:', error);
      console.error('[ChatGroup] ReadyState:', ws.readyState);
      setWsConnected(false);
    };

    ws.onclose = (event) => {
      console.log('[ChatGroup] WebSocket disconnected');
      console.log('[ChatGroup] Close code:', event.code);
      console.log('[ChatGroup] Close reason:', event.reason);
      setWsConnected(false);
    };
  };

    // 发送消息  const sendMessage = () => {
    if (!newMessage.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'send_message',
      content: newMessage.trim(),
      message_type: 'text'
    }));

    setNewMessage('');
  };

// 滚动到底部
const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({behavior: 'smooth'});
  };

  // 选择群聊
  const handleSelectGroup = (group: ChatGroup) => {
    setSelectedGroup(group);
    loadGroupMessages(group.id);
    connectToGroupChat(group.id);
  };

  // 离开群聊
const handleLeaveGroup = async () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setSelectedGroup(null);
    setChatMessages([]);
    setWsConnected(false);
  };

  // 创建群聊
  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) {
        alert('请输入群聊名称');
      return;
    }

    try {
      const response = await apiClient.post('/chat-groups/create', {
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || null,
          member_ids: []  // 不再需要初始成员，通过邀请链接加入
      });

      if (response.success) {
          alert('群聊创建成功！您可以生成邀请链接邀请好友加输入);
        setShowCreateModal(false);
        setNewGroupName('');
        setNewGroupDescription('');
        loadChatGroups();
      } else {
          alert(response.error || '创建失失败');
      }
    } catch (error) {
      console.error('创建群聊失败:', error);
      alert('创建失败，请重试');
    }
  };

// 生成邀请链接
const handleGenerateInvite = async () => {
    if (!selectedGroup) return;

    try {
      const response = await apiClient.post(`/chat-groups/${selectedGroup.id}/create-invite`, {}, {
        params: {
            expires_hours: 72,  // 默认3天过期
            max_uses: null  // 无限制使用次数
        }
      });

      if (response.success) {
        setInviteLink(response.data.full_url);
        setShowInviteModal(true);
      } else {
          alert(response.error || '生成邀请链接失失败');
      }
    } catch (error) {
        console.error('生成邀请链接失失败, error);
      alert('生成失败，请重试');
    }
  };

// 复制邀请链接
const copyInviteLink = () => {
    navigator.clipboard.writeText(inviteLink).then(() => {
        alert('邀请链接已复制到剪贴剪贴板);
    }).catch(err => {
      console.error('复制失败:', err);
        alert('复制失败，请手动复定制);
    });
  };

  // 添加成员
  const handleAddMembers = async () => {
    if (!selectedGroup) return;

    const memberIds = newMemberIds
        .split(',')
        .map(id => parseInt(id.trim()))
        .filter(id => !isNaN(id));

    if (memberIds.length === 0) {
      alert('请输入有效的用户ID');
      return;
    }

    try {
      const response = await apiClient.post(`/chat-groups/${selectedGroup.id}/add-members`, {
        member_ids: memberIds
      });

      if (response.success) {
        alert(`成功添加 ${response.data.added_count} 名成员`);
        setShowAddMemberModal(false);
        setNewMemberIds('');
        loadChatGroups();
      } else {
          alert(response.error || '添加失失败');
      }
    } catch (error) {
      console.error('添加成员失败:', error);
      alert('添加失败，请重试');
    }
  };

  useEffect(() => {
    loadChatGroups();

    // 清理WebSocket连接
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

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
      if (confirm('确定要删除这条消息吗')) {
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
                    {message.sender} · {formatDate(message.date)}
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
                    {message.read ? '已已读 : '未已读}
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
                    发送给 {message.recipient} · {formatDate(message.date)}
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
                    {notification.read ? '已已读 : '未已读}
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

// 渲染群聊标标签  const renderChatTab = () => (
      <div className="flex h-[600px] border rounded-lg overflow-hidden dark:border-gray-700">
        {/* 左侧群聊列表 */}
        <div className="w-1/3 border-r dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="p-4 border-b dark:border-gray-700">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold text-gray-800 dark:text-white">群聊</h3>
              <button
                  onClick={() => setShowCreateModal(true)}
                  className="text-blue-500 hover:text-blue-600"
                  title="创建群聊"
              >
                <FaPlus/>
              </button>
            </div>
          </div>
          <div className="overflow-y-auto h-[calc(100%-64px)]">
            {chatGroups.length > 0 ? (
                chatGroups.map((group) => (
                    <div
                        key={group.id}
                        onClick={() => handleSelectGroup(group)}
                        className={`p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                            selectedGroup?.id === group.id ? 'bg-blue-50 dark:bg-blue-900' : ''
                        }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                            className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-bold">
                          {group.name.charAt(0)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-gray-900 dark:text-white truncate">{group.name}</h4>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            <FaUsers className="inline mr-1"/>
                            {group.member_count} 成员
                          </p>
                        </div>
                      </div>
                    </div>
                ))
            ) : (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  <FaComments className="mx-auto text-4xl mb-2 opacity-50"/>
                  <p>暂无群聊</p>
                </div>
            )}
          </div>
        </div>

        {/* 右侧聊天区域 */}
        <div className="flex-1 flex flex-col">
          {selectedGroup ? (
              <>
                {/* 聊天头部 */}
                <div className="p-4 border-b dark:border-gray-700 flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold text-gray-800 dark:text-white">{selectedGroup.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {wsConnected ? (
                          <span className="text-green-500">● 在线</span>
                      ) : (
                          <span className="text-gray-400">○ 离线</span>
                      )}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                        onClick={handleGenerateInvite}
                        className="text-green-500 hover:text-green-600 transition-colors"
                        title="生成邀请链接
                    >
                      <FaPlus/>
                    </button>
                    <button
                        onClick={() => setShowAddMemberModal(true)}
                        className="text-blue-500 hover:text-blue-600 transition-colors"
                        title="添加成员"
                    >
                      <FaUsers/>
                    </button>
                    <button
                        onClick={handleLeaveGroup}
                        className="text-gray-500 hover:text-red-500 transition-colors"
                        title="离开群聊"
                    >
                      <FaSignOutAlt/>
                    </button>
                  </div>
                </div>

                {/* 消息列表 */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-900">
                  {chatMessages.map((msg) => (
                      <div
                          key={msg.id}
                          className={`flex ${msg.sender === 1 ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                            className={`max-w-[70%] rounded-lg px-4 py-2 ${
                                msg.sender === 1
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow'
                            }`}
                        >
                          <p className="text-sm">{msg.content}</p>
                          <p className={`text-xs mt-1 ${
                              msg.sender === 1 ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
                          }`}>
                            {new Date(msg.created_at).toLocaleTimeString('zh-CN', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                      </div>
                  ))}
                  <div ref={messagesEndRef}/>
                </div>

                {/* 输输入*/}
                <div className="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-800">
                  <div className="flex gap-2">
                    <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        placeholder="输入消息..."
                        className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!wsConnected || !newMessage.trim()}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <FaPaperPlane/>
                    </button>
                  </div>
                </div>
              </>
          ) : (
              <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
                <div className="text-center">
                  <FaComments className="mx-auto text-6xl mb-4 opacity-30"/>
                  <p>选择一个群聊开始聊</p>
                </div>
              </div>
          )}
        </div>
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
                  {loading ? '刷新' : '刷新'}
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
                      收件箱 </button>
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
                  <button
                      onClick={() => setActiveTab('chat')}
                      className={`py-4 px-1 border-b-2 font-medium text-sm ${
                          activeTab === 'chat'
                              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                      }`}
                  >
                    <FaComments className="inline mr-1"/>
                    群聊
                  </button>
                </nav>
              </div>

              <div className="mt-6">
                {activeTab === 'inbox' && renderInboxTab()}
                {activeTab === 'sent' && renderSentTab()}
                {activeTab === 'notifications' && renderNotificationsTab()}
                {activeTab === 'chat' && renderChatTab()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 创建群聊模态框 */}
      {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">创建群聊</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    群聊名称 *
                  </label>
                  <input
                      type="text"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      placeholder="请输入群聊名称
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    群聊描述
                  </label>
                  <textarea
                      value={newGroupDescription}
                      onChange={(e) => setNewGroupDescription(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      placeholder="请输入群聊描述（可选）"
                      rows={3}
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-6">
                <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setNewGroupName('');
                      setNewGroupDescription('');
                      setNewMemberIds('');
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700 dark:text-white"
                >
                  取消
                </button>
                <button
                    onClick={handleCreateGroup}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  创建
                </button>
              </div>
            </div>
          </div>
      )}

      {/* 添加成员模态框 */}
      {showAddMemberModal && selectedGroup && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
                添加成员 - {selectedGroup.name}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    用户ID列表 *
                  </label>
                  <input
                      type="text"
                      value={newMemberIds}
                      onChange={(e) => setNewMemberIds(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      placeholder="输入用户ID，用逗号分隔（如1,2,3）
                  />
                  <p className="text-xs text-gray-500 mt-1">已存在的成员会被自动过滤</p>
                </div>
              </div>

              <div className="flex gap-2 mt-6">
                <button
                    onClick={() => {
                      setShowAddMemberModal(false);
                      setNewMemberIds('');
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700 dark:text-white"
                >
                  取消
                </button>
                <button
                    onClick={handleAddMembers}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
      )}

            {/* 邀请链接模态框 */}
            {showInviteModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
                      <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">邀请链接</h2>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            邀请链接 </label>
                        <div className="flex gap-2">
                          <input
                              type="text"
                              value={inviteLink}
                              readOnly
                              className="flex-1 px-3 py-2 border rounded-lg bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                          <button
                              onClick={copyInviteLink}
                              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 whitespace-nowrap"
                          >
                            复制
                          </button>
                        </div>
                          <p className="text-xs text-gray-500 mt-1">分享此链接邀请好友加入群</p>
                      </div>
                    </div>

                    <div className="flex gap-2 mt-6">
                      <button
                          onClick={() => {
                            setShowInviteModal(false);
                            setInviteLink('');
                          }}
                          className="w-full px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 dark:bg-gray-700 dark:text-white"
                      >
                        关闭
                      </button>
                    </div>
                  </div>
                </div>
            )}
    </WithAuthProtection>
  );
};

export default MessagesPage;