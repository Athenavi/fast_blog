'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Badge} from '@/components/ui/badge';
import {Checkbox} from '@/components/ui/checkbox';
import {Edit, KeyRound, Lock, Plus, Search, Shield, Trash2, Users} from 'lucide-react';
import {toast} from 'sonner';
import {Permission, Role, RoleManagementService, type Stats as RoleStats, type UserRole} from '@/lib/api';

export default function RoleManagementPage() {
  const [activeTab, setActiveTab] = useState<'roles' | 'permissions'>('roles');
  const [roles, setRoles] = useState<UserRole[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [stats, setStats] = useState<RoleStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<Role | UserRole | Permission | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    code: ''
  });
  const [loading, setLoading] = useState(true);

  // Load data from API
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load stats
      const statsResponse = await RoleManagementService.getRolePermissionStats();
      if (statsResponse.success && statsResponse.data) {
        setStats(statsResponse.data as RoleStats);
      }

      // Load roles
      const rolesResponse = await RoleManagementService.getRoles();
      if (rolesResponse.success && rolesResponse.data) {
        setRoles(rolesResponse.data);
      }

      // Load permissions
      const permissionsResponse = await RoleManagementService.getPermissions();
      if (permissionsResponse.success && permissionsResponse.data) {
        setPermissions(permissionsResponse.data);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRole = () => {
    setFormData({ name: '', description: '', code: '' });
    setSelectedPermissions([]);
    setIsEditing(false);
    setCurrentItem(null);
    setIsModalOpen(true);
  };

  const handleEditRole = (role: UserRole) => {
    setFormData({ name: role.name, description: role.description || '', code: '' });
    setSelectedPermissions(role.permissions.map((_: string, index: number) => index));
    setIsEditing(true);
    setCurrentItem(role);
    setIsModalOpen(true);
  };

  const handleDeleteRole = async (roleId: number, roleName: string) => {
    if (confirm(`确定要删除角色 "${roleName}" 吗？此操作不可撤销。`)) {
      try {
        const response = await RoleManagementService.deleteRole(roleId);
        if (response.success) {
          setRoles(roles.filter(role => role.id !== roleId));
          toast.success(`角色 "${roleName}" 已删除`);
          loadData(); // Refresh data
        } else {
          toast.error(response.message || '删除角色失败');
        }
      } catch (error) {
        console.error('Error deleting role:', error);
        toast.error('删除角色失败');
      }
    }
  };

  const handleAddPermission = () => {
    setFormData({ name: '', description: '', code: '' });
    setIsEditing(false);
    setCurrentItem(null);
    setIsModalOpen(true);
  };

  const handleEditPermission = (permission: Permission) => {
    setFormData({ name: '', description: permission.description, code: permission.code });
    setIsEditing(true);
    setCurrentItem(permission);
    setIsModalOpen(true);
  };

  const handleDeletePermission = async (permissionId: number, permissionCode: string) => {
    if (confirm(`确定要删除权限 "${permissionCode}" 吗？此操作不可撤销。`)) {
      try {
        const response = await RoleManagementService.deletePermission(permissionId);
        if (response.success) {
          setPermissions(permissions.filter(permission => permission.id !== permissionId));
          toast.success(`权限 "${permissionCode}" 已删除`);
          loadData(); // Refresh data
        } else {
          toast.error(response.message || '删除权限失败');
        }
      } catch (error) {
        console.error('Error deleting permission:', error);
        toast.error('删除权限失败');
      }
    }
  };

  const handleSaveRole = async () => {
    try {
      let response;
      if (isEditing && currentItem) {
        // Update existing role
        response = await RoleManagementService.updateRole(currentItem.id, {
          name: formData.name,
          description: formData.description,
          permission_ids: selectedPermissions
        });
        
        if (response.success) {
          // Update the role in the local state
          setRoles(roles.map((role: UserRole) => 
            role.id === currentItem.id 
              ? { ...role, name: formData.name, description: formData.description, permissions: permissions.filter((p: Permission) => selectedPermissions.includes(p.id)).map(p => p.code) } 
              : role
          ) as UserRole[]);
          toast.success('角色已更新');
        }
      } else {
        // Add new role
        response = await RoleManagementService.createRole({
          name: formData.name,
          description: formData.description,
          permission_ids: selectedPermissions
        });
        
        if (response.success) {
          setRoles([...roles, (response.data as {data: UserRole}).data]);
          toast.success('角色已添加');
        }
      }
      
      if (response.success) {
        setIsModalOpen(false);
        loadData(); // Refresh data
      } else {
        toast.error(response.message || (isEditing ? '更新角色失败' : '添加角色失败'));
      }
    } catch (error) {
      console.error('Error saving role:', error);
      toast.error(isEditing ? '更新角色失败' : '添加角色失败');
    }
  };

  const handleSavePermission = async () => {
    try {
      let response;
      if (isEditing && currentItem) {
        // Update existing permission
        response = await RoleManagementService.updatePermission(currentItem.id, {
          code: formData.code,
          description: formData.description
        });
        
        if (response.success) {
          // Update the permission in the local state
          setPermissions(permissions.map(permission => 
            permission.id === currentItem.id 
              ? { ...permission, code: formData.code, description: formData.description } 
              : permission
          ));
          toast.success('权限已更新');
        }
      } else {
        // Add new permission
        response = await RoleManagementService.createPermission({
          code: formData.code,
          description: formData.description
        });
        
        if (response.success) {
          setPermissions([...permissions, (response.data as {data: Permission}).data]);
          toast.success('权限已添加');
        }
      }
      
      if (response.success) {
        setIsModalOpen(false);
        loadData(); // Refresh data
      } else {
        toast.error(response.message || (isEditing ? '更新权限失败' : '添加权限失败'));
      }
    } catch (error) {
      console.error('Error saving permission:', error);
      toast.error(isEditing ? '更新权限失败' : '添加权限失败');
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (activeTab === 'roles') {
      handleSaveRole();
    } else {
      handleSavePermission();
    }
  };

  const handlePermissionToggle = (permissionId: number) => {
    setSelectedPermissions(prev => 
      prev.includes(permissionId) 
        ? prev.filter(id => id !== permissionId) 
        : [...prev, permissionId]
    );
  };

  const filteredRoles = roles.filter(role => 
    role.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (role.description && role.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const filteredPermissions = permissions.filter(permission => 
    permission.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    permission.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p>正在加载数据...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">权限管理</h1>
        <p className="text-muted-foreground">管理系统中的角色和权限配置</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Lock className="w-5 h-5 text-blue-600" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">总角色数</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats ? stats.total_roles : '-'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                  <Shield className="w-5 h-5 text-green-600" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">总权限数</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats ? stats.total_permissions : '-'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-purple-600" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">用户角色分配</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats ? stats.total_user_roles : '-'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                  <KeyRound className="w-5 h-5 text-orange-600" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">角色权限分配</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats ? stats.total_role_permissions : '-'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tab Navigation */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'roles' | 'permissions')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="roles">角色管理</TabsTrigger>
          <TabsTrigger value="permissions">权限管理</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Roles Content */}
      {activeTab === 'roles' && (
        <div className="space-y-6">
          {/* Search and Action Bar */}
          <Card>
            <CardContent className="p-4 lg:p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex-1 max-w-md">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="搜索角色名称或描述..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                </div>
                <Button onClick={handleAddRole}>
                  <Plus className="w-4 h-4 mr-2" />
                  添加角色
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Roles List */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>角色信息</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRoles.map((role: UserRole) => (
                      <TableRow key={role.id}>
                        <TableCell>
                          <div>
                            <div className="text-sm font-medium text-gray-900">{role.name}</div>
                            <div className="text-sm text-gray-500">{role.description}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm" onClick={() => handleEditRole(role)}>
                              <Edit className="w-4 h-4 mr-1" />
                              编辑
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => handleDeleteRole(role.id, role.name)}
                              className="text-red-600 hover:text-red-700"
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
        </div>
      )}

      {/* Permissions Content */}
      {activeTab === 'permissions' && (
        <div className="space-y-6">
          {/* Search and Action Bar */}
          <Card>
            <CardContent className="p-4 lg:p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex-1 max-w-md">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="搜索权限代码或描述..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                </div>
                <Button onClick={handleAddPermission}>
                  <Plus className="w-4 h-4 mr-2" />
                  添加权限
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Permissions List */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>权限代码</TableHead>
                      <TableHead>权限描述</TableHead>
                      <TableHead>关联角色</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPermissions.map((permission) => (
                      <TableRow key={permission.id}>
                        <TableCell>
                          <div className="text-sm font-medium text-gray-900">{permission.code}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">{permission.description}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {permission.role_count} 个角色
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm" onClick={() => handleEditPermission(permission)}>
                              <Edit className="w-4 h-4 mr-1" />
                              编辑
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => handleDeletePermission(permission.id, permission.code)}
                              className="text-red-600 hover:text-red-700"
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
        </div>
      )}

      {/* Modal for Role/Permission Form */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {isEditing 
                ? (activeTab === 'roles' ? '编辑角色' : '编辑权限') 
                : (activeTab === 'roles' ? '添加角色' : '添加权限')}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleFormSubmit}>
            {activeTab === 'roles' ? (
              <div className="space-y-4 py-4">
                <div>
                  <Label htmlFor="roleName">角色名称</Label>
                  <Input
                    id="roleName"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </div>
                
                <div>
                  <Label htmlFor="roleDescription">角色描述</Label>
                  <Input
                    id="roleDescription"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    required
                  />
                </div>
                
                <div>
                  <Label>分配权限</Label>
                  <div className="max-h-40 overflow-y-auto border rounded-lg p-3 space-y-2 mt-2">
                    {permissions.map(permission => (
                      <div key={permission.id} className="flex items-center">
                        <Checkbox
                          id={`perm_${permission.id}`}
                          checked={selectedPermissions.includes(permission.id)}
                          onCheckedChange={() => handlePermissionToggle(permission.id)}
                        />
                        <Label htmlFor={`perm_${permission.id}`} className="ml-2 text-sm">
                          {permission.code} - {permission.description}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4 py-4">
                <div>
                  <Label htmlFor="permissionCode">权限代码</Label>
                  <Input
                    id="permissionCode"
                    value={formData.code}
                    onChange={(e) => setFormData({...formData, code: e.target.value})}
                    placeholder="例如: user.create, article.edit"
                    required
                  />
                </div>
                
                <div>
                  <Label htmlFor="permissionDescription">权限描述</Label>
                  <Input
                    id="permissionDescription"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="描述该权限的作用和范围"
                    required
                  />
                </div>
              </div>
            )}
            
            <DialogFooter className="flex sm:justify-between">
              <Button 
                type="button" 
                variant="outline"
                onClick={() => setIsModalOpen(false)}
              >
                取消
              </Button>
              <Button type="submit">
                保存
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}