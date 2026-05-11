/**
 * 权限管理后台 - 角色和权限配置
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Badge} from '@/components/ui/badge';
import {Label} from '@/components/ui/label';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {CheckSquare, Edit, Lock, Plus, Search, Shield, Square, Trash2, Users} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Role {
  id: number;
  name: string;
  slug: string;
  description?: string;
  permissions: string[];
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

interface Permission {
  code: string;
  name: string;
  description?: string;
  category: string;
}

interface User {
  id: number;
  username: string;
  email: string;
  role_id?: number;
  role_name?: string;
}

const PermissionManagement = () => {
  const [activeTab, setActiveTab] = useState('roles');

  // 角色状态
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [roleForm, setRoleForm] = useState({
    name: '',
    slug: '',
    description: '',
    permissions: [] as string[]
  });

  // 权限状态
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [permissionSearch, setPermissionSearch] = useState('');

  // 用户状态
  const [users, setUsers] = useState<User[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [assignRoleDialog, setAssignRoleDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);

  // 加载状态
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRoles();
    loadPermissions();
    loadUsers();
  }, []);

  // 加载角色列表
  const loadRoles = async () => {
    try {
      const response = await apiClient.get('/api/v1/permissions/roles');
      if (response.success && response.data) {
        setRoles((response.data as any).roles || []);
      }
    } catch (error) {
      console.error('Failed to load roles:', error);
    }
  };

  // 加载权限列表
  const loadPermissions = async () => {
    try {
      const response = await apiClient.get('/api/v1/permissions/list');
      if (response.success && response.data) {
        setPermissions((response.data as any).permissions || []);
      }
    } catch (error) {
      console.error('Failed to load permissions:', error);
    }
  };

  // 加载用户列表
  const loadUsers = async () => {
    try {
      const response = await apiClient.get('/api/v1/users?page=1&per_page=100');
      if (response.success && response.data) {
        setUsers((response.data as any).users || []);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  // 打开角色编辑对话框
  const handleEditRole = (role: Role) => {
    setSelectedRole(role);
    setRoleForm({
      name: role.name,
      slug: role.slug,
      description: role.description || '',
      permissions: [...role.permissions]
    });
    setRoleDialogOpen(true);
  };

  // 打开新建角色对话框
  const handleCreateRole = () => {
    setSelectedRole(null);
    setRoleForm({
      name: '',
      slug: '',
      description: '',
      permissions: []
    });
    setRoleDialogOpen(true);
  };

  // 保存角色
  const handleSaveRole = async () => {
    if (!roleForm.name || !roleForm.slug) {
      alert('请填写角色名称和标识');
      return;
    }

    setLoading(true);
    try {
      const data = {
        name: roleForm.name,
        slug: roleForm.slug,
        description: roleForm.description,
        permissions: roleForm.permissions
      };

      let response;
      if (selectedRole) {
        response = await apiClient.put(`/api/v1/permissions/roles/${selectedRole.id}`, data);
      } else {
        response = await apiClient.post('/api/v1/permissions/roles', data);
      }

      if (response.success) {
        setRoleDialogOpen(false);
        loadRoles();
        alert(selectedRole ? '角色更新成功' : '角色创建成功');
      } else {
        alert(response.error || '操作失败');
      }
    } catch (error) {
      console.error('Failed to save role:', error);
      alert('操作失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除角色
  const handleDeleteRole = async (role: Role) => {
    if (role.is_system) {
      alert('系统角色不能删除');
      return;
    }

    if (!confirm(`确定要删除角色 "${role.name}" 吗？`)) {
      return;
    }

    try {
      const response = await apiClient.delete(`/api/v1/permissions/roles/${role.id}`);
      if (response.success) {
        loadRoles();
        alert('角色删除成功');
      } else {
        alert(response.error || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete role:', error);
      alert('删除失败');
    }
  };

  // 切换权限选择
  const togglePermission = (permissionCode: string) => {
    setRoleForm(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permissionCode)
          ? prev.permissions.filter(p => p !== permissionCode)
          : [...prev.permissions, permissionCode]
    }));
  };

  // 全选/取消全选
  const toggleAllPermissions = () => {
    const allCodes = permissions.map(p => p.code);
    const allSelected = allCodes.every(code => roleForm.permissions.includes(code));

    setRoleForm(prev => ({
      ...prev,
      permissions: allSelected ? [] : allCodes
    }));
  };

  // 按分类分组权限
  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.category]) {
      acc[perm.category] = [];
    }
    acc[perm.category].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  // 过滤权限
  const filteredPermissions = permissions.filter(p =>
      p.name.toLowerCase().includes(permissionSearch.toLowerCase()) ||
      p.code.toLowerCase().includes(permissionSearch.toLowerCase())
  );

  // 过滤用户
  const filteredUsers = users.filter(u =>
      u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase())
  );

  // 分配角色给用户
  const handleAssignRole = async () => {
    if (!selectedUser || !selectedRoleId) {
      alert('请选择用户和角色');
      return;
    }

    try {
      const response = await apiClient.post('/api/v1/permissions/users/assign-role', {
        user_id: selectedUser.id,
        role_id: selectedRoleId
      });

      if (response.success) {
        setAssignRoleDialog(false);
        loadUsers();
        alert('角色分配成功');
      } else {
        alert(response.error || '分配失败');
      }
    } catch (error) {
      console.error('Failed to assign role:', error);
      alert('分配失败');
    }
  };

  const openAssignRoleDialog = (user: User) => {
    setSelectedUser(user);
    setSelectedRoleId(user.role_id || null);
    setAssignRoleDialog(true);
  };

  return (
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">权限管理</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              管理角色、权限和用户角色分配
            </p>
          </div>
        </div>

        {/* 标签页 */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="roles" className="flex items-center gap-2">
              <Shield className="w-4 h-4"/>
              角色管理
            </TabsTrigger>
            <TabsTrigger value="permissions" className="flex items-center gap-2">
              <Lock className="w-4 h-4"/>
              权限列表
            </TabsTrigger>
            <TabsTrigger value="users" className="flex items-center gap-2">
              <Users className="w-4 h-4"/>
              用户角色
            </TabsTrigger>
          </TabsList>

          {/* 角色管理 */}
          <TabsContent value="roles" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>角色列表</CardTitle>
                    <CardDescription>管理系统角色和自定义角色</CardDescription>
                  </div>
                  <Button onClick={handleCreateRole}>
                    <Plus className="w-4 h-4 mr-2"/>
                    新建角色
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {roles.map((role) => (
                      <div
                          key={role.id}
                          className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-medium text-gray-900 dark:text-white">
                              {role.name}
                            </h3>
                            {role.is_system && (
                                <Badge variant="secondary">系统角色</Badge>
                            )}
                            <Badge variant="outline">
                              {role.permissions.length} 个权限
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {role.description || '无描述'}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            标识: {role.slug}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEditRole(role)}
                          >
                            <Edit className="w-4 h-4"/>
                          </Button>
                          {!role.is_system && (
                              <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleDeleteRole(role)}
                                  className="text-red-600 hover:text-red-700"
                              >
                                <Trash2 className="w-4 h-4"/>
                              </Button>
                          )}
                        </div>
                      </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 权限列表 */}
          <TabsContent value="permissions" className="space-y-4">
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>权限列表</CardTitle>
                  <CardDescription>系统所有可用权限</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                    <Input
                        placeholder="搜索权限..."
                        value={permissionSearch}
                        onChange={(e) => setPermissionSearch(e.target.value)}
                        className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  {Object.entries(groupedPermissions).map(([category, perms]) => (
                      <div key={category}>
                        <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                          {category}
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {perms
                              .filter(p =>
                                  p.name.toLowerCase().includes(permissionSearch.toLowerCase()) ||
                                  p.code.toLowerCase().includes(permissionSearch.toLowerCase())
                              )
                              .map((perm) => (
                                  <div
                                      key={perm.code}
                                      className="p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                  >
                                    <div className="font-medium text-sm text-gray-900 dark:text-white">
                                      {perm.name}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                      {perm.code}
                                    </div>
                                    {perm.description && (
                                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                          {perm.description}
                                        </div>
                                    )}
                                  </div>
                              ))}
                        </div>
                      </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 用户角色 */}
          <TabsContent value="users" className="space-y-4">
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>用户角色分配</CardTitle>
                  <CardDescription>为用户分配和管理角色</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                    <Input
                        placeholder="搜索用户..."
                        value={userSearch}
                        onChange={(e) => setUserSearch(e.target.value)}
                        className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  {filteredUsers.map((user) => (
                      <div
                          key={user.id}
                          className="flex items-center justify-between p-4 border rounded-lg"
                      >
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {user.username}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">
                            {user.email}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={user.role_name ? "default" : "outline"}>
                            {user.role_name || '未分配'}
                          </Badge>
                          <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openAssignRoleDialog(user)}
                          >
                            分配角色
                          </Button>
                        </div>
                      </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 角色编辑对话框 */}
        <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {selectedRole ? '编辑角色' : '新建角色'}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* 基本信息 */}
              <div className="space-y-3">
                <div>
                  <Label htmlFor="role-name">角色名称</Label>
                  <Input
                      id="role-name"
                      value={roleForm.name}
                      onChange={(e) => setRoleForm({...roleForm, name: e.target.value})}
                      placeholder="例如：内容编辑"
                  />
                </div>

                <div>
                  <Label htmlFor="role-slug">角色标识</Label>
                  <Input
                      id="role-slug"
                      value={roleForm.slug}
                      onChange={(e) => setRoleForm({...roleForm, slug: e.target.value})}
                      placeholder="例如：content_editor"
                  />
                </div>

                <div>
                  <Label htmlFor="role-description">角色描述</Label>
                  <Textarea
                      id="role-description"
                      value={roleForm.description}
                      onChange={(e) => setRoleForm({...roleForm, description: e.target.value})}
                      placeholder="描述该角色的职责和权限范围"
                      rows={3}
                  />
                </div>
              </div>

              {/* 权限选择 */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label>权限配置</Label>
                  <Button
                      size="sm"
                      variant="outline"
                      onClick={toggleAllPermissions}
                  >
                    {permissions.every(p => roleForm.permissions.includes(p.code))
                        ? '取消全选'
                        : '全选'}
                  </Button>
                </div>

                <div className="space-y-4 max-h-96 overflow-y-auto border rounded-lg p-4">
                  {Object.entries(groupedPermissions).map(([category, perms]) => (
                      <div key={category}>
                        <h4 className="font-medium text-sm text-gray-900 dark:text-white mb-2">
                          {category}
                        </h4>
                        <div className="space-y-2">
                          {perms.map((perm) => {
                            const isSelected = roleForm.permissions.includes(perm.code);
                            return (
                                <div
                                    key={perm.code}
                                    className="flex items-start gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded cursor-pointer"
                                    onClick={() => togglePermission(perm.code)}
                                >
                                  {isSelected ? (
                                      <CheckSquare className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5"/>
                                  ) : (
                                      <Square className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5"/>
                                  )}
                                  <div className="flex-1">
                                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                                      {perm.name}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      {perm.code}
                                    </div>
                                    {perm.description && (
                                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                          {perm.description}
                                        </div>
                                    )}
                                  </div>
                                </div>
                            );
                          })}
                        </div>
                      </div>
                  ))}
                </div>

                <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  已选择 {roleForm.permissions.length} 个权限
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSaveRole} disabled={loading}>
                {loading ? '保存中...' : '保存'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 分配角色对话框 */}
        <Dialog open={assignRoleDialog} onOpenChange={setAssignRoleDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>分配角色</DialogTitle>
            </DialogHeader>

            <div className="py-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                为用户 <strong>{selectedUser?.username}</strong> 分配角色
              </p>

              <div className="space-y-2">
                <Label>选择角色</Label>
                <div className="space-y-2 max-h-60 overflow-y-auto border rounded-lg p-3">
                  {roles.map((role) => (
                      <div
                          key={role.id}
                          className={`flex items-center gap-2 p-2 rounded cursor-pointer ${
                              selectedRoleId === role.id
                                  ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 border'
                                  : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}
                          onClick={() => setSelectedRoleId(role.id)}
                      >
                        <input
                            type="radio"
                            checked={selectedRoleId === role.id}
                            onChange={() => setSelectedRoleId(role.id)}
                            className="w-4 h-4"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-sm">{role.name}</div>
                          <div className="text-xs text-gray-500">{role.description}</div>
                        </div>
                      </div>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAssignRoleDialog(false)}>
                取消
              </Button>
              <Button onClick={handleAssignRole}>
                确认分配
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
  );
};

export default PermissionManagement;
