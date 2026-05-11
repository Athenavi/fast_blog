'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Badge} from '@/components/ui/badge';
import {Checkbox} from '@/components/ui/checkbox';
import {CheckCircle, Edit, Eye, EyeOff, Plus, Search, Trash2, User} from 'lucide-react';
import {toast} from 'sonner';
import {type Pagination, RoleManagementService, UserManagementService, type UserWithRoles} from '@/lib/api';
import {UserRoleService} from "@/lib/api/user-management-service";
import {UserRole} from "@/lib/api/base-types";
import ScreenOptions from '@/components/ScreenOptions';

export default function UserManagementPage() {
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [allRoles, setAllRoles] = useState<UserRole[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    current_page: 1,
    per_page: 10,
    total: 0,
    total_pages: 1,
    has_prev: false,
    has_next: false
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserWithRoles | null>(null);
  const [userToDelete, setUserToDelete] = useState<{ id: number; name: string } | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    bio: '',
    profilePicture: ''
  });

  // 可见列状态
  const [visibleColumns, setVisibleColumns] = useState<string[]>([
    'username', 'email', 'roles', 'date_joined', 'media_count', 'comment_count'
  ]);

  // 选中的用户ID
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);

  // 处理屏幕选项变化
  const handleScreenOptionsChange = (options: any) => {
    console.log('Screen options changed:', options);

    // 应用per_page选项
    if (options.per_page && options.per_page !== pagination.per_page) {
      setPagination(prev => ({
        ...prev,
        per_page: options.per_page,
        current_page: 1 // 重置到第一页
      }));
    }

    // 应用columns选项
    if (options.columns && Array.isArray(options.columns)) {
      console.log('Updating visible columns:', options.columns);
      setVisibleColumns(options.columns);
    }
  };

  // Load users and roles from API
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Load users
        const usersResponse = await UserManagementService.getUsers({
          page: pagination.current_page, 
          per_page: pagination.per_page,
          search: searchQuery 
        });

        let updatedUsers: UserWithRoles[] = [];
        let updatedPagination = {...pagination};
        
        if (usersResponse.success && usersResponse.data) {
          updatedUsers = usersResponse.data.users || [];
          updatedPagination = usersResponse.data.pagination || pagination;
          setUsers(updatedUsers);
          setPagination(updatedPagination);
        } else {
          console.error('Failed to load users:', usersResponse.error);
          toast.error('加载用户数据失败');
        }

        // Load roles
        const rolesResponse = await RoleManagementService.getRoles();
        
        if (rolesResponse.success && rolesResponse.data) {
          // 后端返回的数据结构是 {roles: [...]}
          const rolesData = (rolesResponse.data as any).roles || rolesResponse.data;
          setAllRoles(Array.isArray(rolesData) ? rolesData : []);
        } else {
          console.error('Failed to load roles:', rolesResponse.error);
          toast.error('加载角色数据失败');
        }

        // Load screen options
        try {
          const config = await import('@/lib/config');
          const screenOptionsResponse = await fetch(
              `${config.getConfig().API_BASE_URL}${config.getConfig().API_PREFIX}/screen-options/options?page_name=users`,
              {credentials: 'include'}
          );

          if (screenOptionsResponse.ok) {
            const screenOptionsResult = await screenOptionsResponse.json();
            if (screenOptionsResult.success && screenOptionsResult.data?.columns) {
              console.log('Loaded saved columns:', screenOptionsResult.data.columns);
              setVisibleColumns(screenOptionsResult.data.columns);
            }
          }
        } catch (error) {
          console.warn('Failed to load screen options:', error);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        toast.error('获取数据时发生错误');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [pagination.current_page, pagination.per_page, searchQuery]);

  const handleAddUser = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      bio: '',
      profilePicture: ''
    });
    setIsEditing(false);
    setCurrentUser(null);
    setIsModalOpen(true);
  };

  const handleEditUser = (user: UserWithRoles) => {
    setFormData({
      username: user.username,
      email: user.email,
      password: '',
      bio: user.bio || '',
      profilePicture: user.profile_picture || ''
    });
    setIsEditing(true);
    setCurrentUser(user);
    setIsModalOpen(true);
  };

  const handleDeleteUser = (userId: number, userName: string) => {
    setUserToDelete({ id: userId, name: userName });
    setIsDeleteModalOpen(true);
  };

  const confirmDeleteUser = async () => {
    if (userToDelete) {
      try {
        const response = await UserManagementService.deleteUser(userToDelete.id);
        
        if (response.success) {
          setUsers(users.filter(user => user.id !== userToDelete.id));
          toast.success(`用户 "${userToDelete.name}" 已删除`);
        } else {
          console.error('Failed to delete user:', response.error);
          toast.error(response.error || '删除用户失败');
        }
      } catch (error) {
        console.error('Error deleting user:', error);
        toast.error('删除用户时发生错误');
      }
      
      setIsDeleteModalOpen(false);
      setUserToDelete(null);
    }
  };

  const handleAssignRoles = (user: UserWithRoles) => {
    setSelectedRoles(user.roles ? user.roles.map(role => role.id) : []);
    setCurrentUser(user);
    setIsRoleModalOpen(true);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (isEditing && currentUser) {
        // Update existing user
        const response = await UserManagementService.updateUser(currentUser.id, {
          username: formData.username,
          email: formData.email,
          bio: formData.bio,
          profile_picture: formData.profilePicture
        });
        
        if (response.success && response.data) {
          setUsers(users.map(user => 
            user.id === currentUser.id 
              ? { 
                  ...user, 
                  username: formData.username, 
                  email: formData.email, 
                  bio: formData.bio,
                  profile_picture: formData.profilePicture
                } 
              : user
          ));
          toast.success('用户信息已更新');
        } else {
          console.error('Failed to update user:', response.error);
          toast.error(response.error || '更新用户失败');
        }
      } else {
        // Add new user
        const response = await UserManagementService.createUser({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          bio: formData.bio,
          profile_picture: formData.profilePicture
        });
        
        if (response.success && response.data) {
          setUsers([...users, response.data]);
          toast.success('用户已添加');
        } else {
          console.error('Failed to create user:', response.error);
          toast.error(response.error || '添加用户失败');
        }
      }
      
      setIsModalOpen(false);
    } catch (error) {
      console.error('Error saving user:', error);
      toast.error('保存用户时发生错误');
    }
  };

  const handleSaveRoles = async () => {
    if (currentUser) {
      try {
        const response = await UserRoleService.assignRolesToUser(currentUser.id, selectedRoles);
        
        if (response.success) {
          // 更新本地用户数据
          const updatedRoles = allRoles.filter(role => selectedRoles.includes(role.id));
          
          setUsers(users.map(user => 
            user.id === currentUser.id 
              ? { ...user, roles: updatedRoles } 
              : user
          ));
          
          toast.success('用户角色已更新');
          setIsRoleModalOpen(false);
        } else {
          console.error('Failed to assign roles:', response.error);
          toast.error(response.error || '分配角色失败');
        }
      } catch (error) {
        console.error('Error assigning roles:', error);
        toast.error('分配角色时发生错误');
      }
    }
  };

  const handleRoleToggle = (roleId: number) => {
    setSelectedRoles(prev => 
      prev.includes(roleId) 
        ? prev.filter(id => id !== roleId) 
        : [...prev, roleId]
    );
  };

  // 切换用户选择
  const toggleUserSelection = (userId: number) => {
    setSelectedUserIds(prev =>
        prev.includes(userId)
            ? prev.filter(id => id !== userId)
            : [...prev, userId]
    );
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedUserIds.length === filteredUsers.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.map(user => user.id));
    }
  };

  // CSV导出功能
  const handleExportCSV = () => {
    try {
      // 确定要导出的用户：如果有选中的用户，只导出选中的；否则导出所有过滤后的用户
      const usersToExport = selectedUserIds.length > 0
          ? filteredUsers.filter(user => selectedUserIds.includes(user.id))
          : filteredUsers;

      if (usersToExport.length === 0) {
        toast.warning('没有可导出的用户数据');
        return;
      }

      console.log('Exporting users:', usersToExport.length, 'users');
      console.log('Visible columns:', visibleColumns);

      // 定义列映射（key -> 英文CSV列名）
      const columnMap: Record<string, { csvHeader: string; getValue: (user: UserWithRoles) => string }> = {
        username: {
          csvHeader: 'username',
          getValue: (user) => user.username
        },
        email: {
          csvHeader: 'email',
          getValue: (user) => user.email
        },
        roles: {
          csvHeader: 'roles',
          getValue: (user) => user.roles && user.roles.length > 0
              ? user.roles.map(r => r.name).join(', ')
              : ''
        },
        date_joined: {
          csvHeader: 'created_at',
          getValue: (user) => user.created_at
              ? new Date(user.created_at).toISOString()
              : ''
        },
        media_count: {
          csvHeader: 'media_count',
          getValue: (user) => String(user.media_count || 0)
        },
        comment_count: {
          csvHeader: 'comment_count',
          getValue: (user) => String(user.comment_count || 0)
        }
      };

      // 构建CSV内容 - 使用英文列名
      const headers = visibleColumns.map(col => columnMap[col]?.csvHeader || col);
      const csvRows = [headers.join(',')]; // 表头

      usersToExport.forEach(user => {
        const row = visibleColumns.map(col => {
          const value = columnMap[col]?.getValue(user) || '';
          // 如果值包含逗号或引号，需要用引号包裹并转义
          return value.includes(',') || value.includes('"')
              ? `"${value.replace(/"/g, '""')}"`
              : value;
        });
        csvRows.push(row.join(','));
      });

      const csvContent = csvRows.join('\n');

      // 添加BOM以支持中文
      const BOM = '\uFEFF';
      const blob = new Blob([BOM + csvContent], {type: 'text/csv;charset=utf-8;'});
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = selectedUserIds.length > 0
          ? `users_selected_${selectedUserIds.length}_${new Date().toISOString().split('T')[0]}.csv`
          : `users_all_${filteredUsers.length}_${new Date().toISOString().split('T')[0]}.csv`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`已导出 ${usersToExport.length} 个用户的数据`);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      toast.error('导出失败');
    }
  };

  // CSV导入功能
  const handleImportCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    if (!file.name.endsWith('.csv')) {
      toast.error('请上传CSV文件');
      e.target.value = '';
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('Importing CSV file:', file.name);

      const config = await import('@/lib/config');
      const response = await fetch(
          `${config.getConfig().API_BASE_URL}${config.getConfig().API_PREFIX}/users/import-csv`,
          {
            method: 'POST',
            credentials: 'include',
            body: formData,
          }
      );

      const result = await response.json();

      if (!result.success) {
        // 构建错误提示信息
        let errorMessage = result.error || '导入失败';
        
        // 如果是字段缺失或格式错误，显示详细要求
        if (result.data?.errors && result.data.errors.length > 0) {
          console.error('CSV解析错误:', result.data.errors);
          
          // 检查是否是用户名空的错误
          const hasUsernameError = result.data.errors.some((err: string) => 
            err.includes('用户名') || err.includes('username')
          );
          
          if (hasUsernameError || result.data.errors.length <= 5) {
            // 显示所有错误
            errorMessage += '\n\n错误详情:\n';
            result.data.errors.forEach((err: string, index: number) => {
              if (index < 10) { // 最多显示10个错误
                errorMessage += `• ${err}\n`;
              }
            });
            if (result.data.errors.length > 10) {
              errorMessage += `...还有 ${result.data.errors.length - 10} 个错误`;
            }
          }
        }
        
        // 显示主要错误
        toast.error(errorMessage);
        
        // 如果有错误，显示格式要求提示
        if (result.data?.errors && result.data.errors.length > 0) {
          setTimeout(() => {
            showImportHelpDialog();
          }, 100);
        }
        
        return;
      }

      toast.success(result.data.message || '导入成功');
      
      // 刷新用户列表
      const usersResponse = await UserManagementService.getUsers({
        page: pagination.current_page,
        per_page: pagination.per_page,
      });
      
      if (usersResponse.success && usersResponse.data) {
        setUsers(usersResponse.data.users || []);
        setPagination(usersResponse.data.pagination || pagination);
      }
    } catch (error) {
      console.error('Error importing CSV:', error);
      toast.error('导入失败：网络错误或服务器无响应');
    } finally {
      // 清空文件输入
      e.target.value = '';
    }
  };

  // 显示导入帮助对话框
  const showImportHelpDialog = () => {
    // 创建一个自定义的HTML对话框，包含下载按钮
    const dialogHtml = `
      <div style="text-align: left; max-width: 600px;">
        <h3 style="margin-top: 0; color: #2563eb;">📋 CSV导入格式要求</h3>
        <hr style="margin: 16px 0; border: none; border-top: 1px solid #e5e7eb;" />
        
        <h4 style="color: #374151; margin-bottom: 8px;">【必需列】</h4>
        <ul style="margin: 0; padding-left: 20px; color: #4b5563;">
          <li><strong>username</strong> - 用户名（不能为空）</li>
          <li><strong>email</strong> - 邮箱地址</li>
          <li><strong>password</strong> - 密码（新建用户时必需）</li>
        </ul>
        
        <h4 style="color: #374151; margin: 16px 0 8px 0;">【可选列】</h4>
        <ul style="margin: 0; padding-left: 20px; color: #4b5563;">
          <li><strong>roles</strong> - 角色名称，多个用逗号分隔（如：管理员,VIP用户）</li>
          <li><strong>bio</strong> - 个人简介</li>
          <li><strong>created_at</strong> - 创建时间（ISO格式，如：2026-04-22T10:30:00.000Z）</li>
          <li><strong>media_count</strong> - 媒体文件数</li>
          <li><strong>comment_count</strong> - 评论数</li>
        </ul>
        
        <h4 style="color: #374151; margin: 16px 0 8px 0;">【CSV示例】</h4>
        <pre style="background: #f3f4f6; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto;">username,email,password,roles,bio
zhangsan,zhang@example.com,123456,管理员,这是一个测试用户
lisi,lisi@example.com,123456,,
wangwu,wang@example.com,123456,编辑;VIP用户,另一个用户</pre>
        
        <h4 style="color: #374151; margin: 16px 0 8px 0;">💡 提示：</h4>
        <ol style="margin: 0; padding-left: 20px; color: #4b5563;">
          <li>第一行必须是列名（使用英文）</li>
          <li>可以使用导出的CSV作为模板</li>
          <li>更新现有用户时，password可为空</li>
          <li>角色名称必须与系统中已有的角色匹配</li>
        </ol>
        
        <div style="margin-top: 20px; text-align: center;">
          <button id="downloadSampleBtn" style="
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
          ">📥 下载示例CSV模板</button>
        </div>
      </div>
    `;
    
    // 创建对话框
    const dialog = document.createElement('div');
    dialog.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
      background: white;
      padding: 24px;
      border-radius: 12px;
      max-width: 650px;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    `;
    content.innerHTML = dialogHtml;
    
    // 点击背景关闭
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) {
        document.body.removeChild(dialog);
      }
    });
    
    // 下载按钮事件
    const downloadBtn = content.querySelector('#downloadSampleBtn');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', async () => {
        try {
          const config = await import('@/lib/config');
          const response = await fetch(
            `${config.getConfig().API_BASE_URL}${config.getConfig().API_PREFIX}/users/download-sample-csv`,
            { credentials: 'include' }
          );
          
          if (!response.ok) {
            throw new Error('下载失败');
          }
          
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'user_import_sample.csv';
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          
          toast.success('示例CSV已下载');
          document.body.removeChild(dialog);
        } catch (error) {
          console.error('Error downloading sample CSV:', error);
          toast.error('下载失败');
        }
      });
    }
    
    dialog.appendChild(content);
    document.body.appendChild(dialog);
  };

  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.bio?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">用户管理</h1>
            <p className="text-gray-600 mt-1">管理网站的所有用户账户</p>
          </div>
          <Button onClick={handleAddUser} className="bg-blue-600 hover:bg-blue-700">
            <Plus className="w-4 h-4 mr-2" />
            添加用户
          </Button>
        </div>
      </div>

      {/* 用户统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border border-gray-200">
          <CardContent className="p-5">
            <div className="flex items-center">
              <div className="bg-blue-100 p-3 rounded-lg">
                <User className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">总用户数</p>
                <p className="text-2xl font-bold">{users.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardContent className="p-5">
            <div className="flex items-center">
              <div className="bg-green-100 p-3 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">活跃用户</p>
                <p className="text-2xl font-bold">{users.filter(u => u.roles && u.roles.some(r => r.name !== '普通用户')).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardContent className="p-5">
            <div className="flex items-center">
              <div className="bg-purple-100 p-3 rounded-lg">
                <User className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">VIP用户</p>
                <p className="text-2xl font-bold">{users.filter(u => u.roles && u.roles.some(r => r.name === 'VIP用户')).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardContent className="p-5">
            <div className="flex items-center">
              <div className="bg-yellow-100 p-3 rounded-lg">
                <User className="w-6 h-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">管理员</p>
                <p className="text-2xl font-bold">{users.filter(u => u.roles && u.roles.some(r => r.name === '管理员')).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 搜索和筛选栏 */}
      <Card className="border border-gray-200">
        <CardContent className="p-4 border-b">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="搜索用户..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-full"
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {selectedUserIds.length > 0 && (
                  <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium">
                    已选择 {selectedUserIds.length} 个用户
                  </div>
              )}
              <ScreenOptions 
                pageName="users"
                availableColumns={[
                  { key: 'username', label: '用户名' },
                  { key: 'email', label: '邮箱' },
                  { key: 'roles', label: '角色' },
                  { key: 'date_joined', label: '注册时间' },
                  { key: 'media_count', label: '媒体文件' },
                  { key: 'comment_count', label: '评论数' },
                ]}
                defaultPerPage={pagination.per_page}
                onOptionsChange={handleScreenOptionsChange}
              />
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleExportCSV}
              >
                导出CSV
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => document.getElementById('csv-import-input')?.click()}
              >
                导入CSV
              </Button>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={showImportHelpDialog}
                className="text-blue-600 hover:text-blue-700"
              >
                ❓ 格式说明
              </Button>
              <input
                id="csv-import-input"
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleImportCSV}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 用户表格 */}
      <Card className="border border-gray-200">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="min-w-full divide-y divide-gray-200">
              <TableHeader className="bg-gray-50">
                <TableRow>
                  <TableHead className="px-6 py-3 text-left">
                    <Checkbox
                        checked={selectedUserIds.length === filteredUsers.length && filteredUsers.length > 0}
                        onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  {visibleColumns.includes('username') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        用户
                      </TableHead>
                  )}
                  {visibleColumns.includes('email') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        邮箱
                      </TableHead>
                  )}
                  {visibleColumns.includes('roles') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        角色
                      </TableHead>
                  )}
                  {visibleColumns.includes('date_joined') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        注册时间
                      </TableHead>
                  )}
                  {visibleColumns.includes('media_count') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        媒体文件
                      </TableHead>
                  )}
                  {visibleColumns.includes('comment_count') && (
                      <TableHead
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        评论数
                      </TableHead>
                  )}
                  <TableHead className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="bg-white divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <TableRow key={user.id} className="hover:bg-gray-50">
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      <Checkbox
                          checked={selectedUserIds.includes(user.id)}
                          onCheckedChange={() => toggleUserSelection(user.id)}
                      />
                    </TableCell>
                    {visibleColumns.includes('username') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-10 w-10">
                              {user.profile_picture ? (
                                  <img
                                      src={`/static/avatar/${user.profile_picture}.webp`}
                                      alt={user.username}
                                      className="h-10 w-10 rounded-full object-cover"
                                      onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        target.onerror = null;
                                        target.src = `/static/avatar/default.webp`;
                                      }}
                                  />
                              ) : (
                                  <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                                <span className="text-gray-700 font-medium">
                                  {user.username.charAt(0).toUpperCase()}
                                </span>
                                  </div>
                              )}
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-gray-900">{user.username}</div>
                              {user.bio && (
                                  <div className="text-sm text-gray-500 truncate max-w-xs">
                                    {user.bio}
                                  </div>
                              )}
                            </div>
                          </div>
                        </TableCell>
                    )}
                    {visibleColumns.includes('email') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{user.email}</div>
                        </TableCell>
                    )}
                    {visibleColumns.includes('roles') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap">
                          <div className="flex flex-wrap gap-1">
                            {user.roles && user.roles.length > 0 ? (
                                user.roles.map(role => (
                                    <Badge key={role.id} variant="secondary" className="text-xs">
                                      {role.name}
                                    </Badge>
                                ))
                            ) : (
                                <span className="text-gray-400 text-xs">无角色</span>
                            )}
                          </div>
                        </TableCell>
                    )}
                    {visibleColumns.includes('date_joined') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN') : '-'}
                        </TableCell>
                    )}
                    {visibleColumns.includes('media_count') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.media_count || 0}
                        </TableCell>
                    )}
                    {visibleColumns.includes('comment_count') && (
                        <TableCell className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.comment_count || 0}
                        </TableCell>
                    )}
                    <TableCell className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleEditUser(user)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          编辑
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleAssignRoles(user)}
                          className="text-green-600 hover:text-green-900"
                        >
                          角色
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleDeleteUser(user.id, user.username)}
                          className="text-red-600 hover:text-red-900"
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* 分页 */}
      {pagination.total_pages && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex flex-1 justify-between sm:hidden">
            <Button 
              variant="outline" 
              onClick={() => setPagination(prev => ({
                ...prev,
                current_page: Math.max(1, prev.current_page - 1)
              }))}
              disabled={!pagination.has_prev}
            >
              上一页
            </Button>
            <Button 
              variant="outline" 
              className="ml-3"
              onClick={() => setPagination(prev => ({
                ...prev,
                current_page: Math.min(prev.total_pages || 1, prev.current_page + 1)
              }))}
              disabled={!pagination.has_next}
            >
              下一页
            </Button>
          </div>
          <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                显示第 <span className="font-medium">{(pagination.current_page - 1) * pagination.per_page + 1}</span> 到{' '}
                <span className="font-medium">{Math.min(pagination.current_page * pagination.per_page, pagination.total)}</span>{' '}
                条，共 <span className="font-medium">{pagination.total}</span> 条
              </p>
            </div>
            <div>
              <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                <Button
                  variant="outline"
                  onClick={() => setPagination(prev => ({
                    ...prev,
                    current_page: Math.max(1, prev.current_page - 1)
                  }))}
                  disabled={!pagination.has_prev}
                  className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">上一页</span>
                  上一页
                </Button>
                
                {Array.from({ length: pagination.total_pages || 0 }, (_, i) => i + 1).map(pageNum => (
                  <Button
                    key={pageNum}
                    variant={pagination.current_page === pageNum ? "default" : "outline"}
                    onClick={() => setPagination(prev => ({ ...prev, current_page: pageNum }))}
                    className={`relative inline-flex items-center ${
                      pagination.current_page === pageNum 
                        ? 'z-10 bg-blue-600 border-blue-600 text-white' 
                        : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50'
                    } px-4 py-2 text-sm font-medium focus:z-20 focus:outline-offset-0`}
                  >
                    {pageNum}
                  </Button>
                ))}
                
                <Button
                  variant="outline"
                  onClick={() => setPagination(prev => ({
                    ...prev,
                    current_page: Math.min(prev.total_pages || 1, prev.current_page + 1)
                  }))}
                  disabled={!pagination.has_next}
                  className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">下一页</span>
                  下一页
                </Button>
              </nav>
            </div>
          </div>
        </div>
      )}

      {/* 添加/编辑用户模态框 */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-md sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {isEditing ? '编辑用户' : '添加用户'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSaveUser}>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="username">用户名 *</Label>
                <Input
                  id="username"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  required
                />
              </div>
              
              <div>
                <Label htmlFor="email">邮箱 *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              
              <div>
                <Label htmlFor="password">密码 *</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {isEditing ? '编辑时留空表示不修改密码' : '请输入用户密码'}
                </p>
              </div>
              
              <div>
                <Label htmlFor="bio">个人简介</Label>
                <Input
                  id="bio"
                  value={formData.bio}
                  onChange={(e) => setFormData({...formData, bio: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="profilePicture">头像URL</Label>
                <Input
                  id="profilePicture"
                  value={formData.profilePicture}
                  onChange={(e) => setFormData({...formData, profilePicture: e.target.value})}
                />
              </div>
            </div>
            
            <DialogFooter className="flex sm:justify-between">
              <Button 
                type="button" 
                variant="outline"
                onClick={() => setIsModalOpen(false)}
              >
                取消
              </Button>
              <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                {isEditing ? '更新' : '添加'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 删除确认模态框 */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>
              确定要删除用户 <span className="font-medium">&#34;{userToDelete?.name}&#34;</span> 吗？
            </p>
            <p className="text-sm text-gray-500 mt-2">
              此操作不可撤销，用户的所有数据将被永久删除。
            </p>
          </div>
          <DialogFooter className="flex sm:justify-between">
            <Button 
              variant="outline"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              取消
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmDeleteUser}
            >
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 分配用户角色模态框 */}
      <Dialog open={isRoleModalOpen} onOpenChange={setIsRoleModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>分配用户角色</DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            <p className="text-sm text-gray-600 mb-4">
              用户: <span className="font-medium">{currentUser?.username}</span>
            </p>
            
            <div className="max-h-64 overflow-y-auto border rounded-lg p-3 space-y-2">
              {allRoles.map(role => (
                <div key={role.id} className="flex items-start">
                  <Checkbox
                    id={`role_${role.id}`}
                    checked={selectedRoles.includes(role.id)}
                    onCheckedChange={() => handleRoleToggle(role.id)}
                  />
                  <Label htmlFor={`role_${role.id}`} className="ml-2 text-sm flex-1">
                    <div className="font-medium">{role.name}</div>
                    <div className="text-xs text-gray-500">{role.description}</div>
                  </Label>
                </div>
              ))}
            </div>
          </div>
          
          <DialogFooter className="flex sm:justify-between">
            <Button 
              type="button" 
              variant="outline"
              onClick={() => setIsRoleModalOpen(false)}
            >
              取消
            </Button>
            <Button onClick={handleSaveRoles} className="bg-blue-600 hover:bg-blue-700">
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}