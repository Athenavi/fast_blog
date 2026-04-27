'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Badge} from '@/components/ui/badge';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {ChevronLeft, ChevronRight, Crown, Edit, Plus, Receipt, Star, Trash2} from 'lucide-react';
import {toast} from 'sonner';

interface VipPlan {
  id: number;
  name: string;
  description?: string;
  price: number;
  duration_days: number;
  level: number;
  features?: string;
  is_active: boolean;
}

interface VipFeature {
  id: number;
  code: string;
  name: string;
  description?: string;
  required_level: number;
  is_active: boolean;
}

interface Subscription {
  id: number;
  user_id: number;
  plan_id: number;
  plan_name: string;
  starts_at: string;
  expires_at: string;
  payment_amount: number;
  transaction_id?: string;
  status: number;
}

export default function VipManagementPage() {
  const [activeTab, setActiveTab] = useState<'plans' | 'subscriptions' | 'features'>('plans');
  const [plans, setPlans] = useState<VipPlan[]>([]);
  const [features, setFeatures] = useState<VipFeature[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [isFeatureModalOpen, setIsFeatureModalOpen] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<VipPlan | null>(null);
  const [currentFeature, setCurrentFeature] = useState<VipFeature | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: 0,
    duration_days: 30,
    level: 1,
    features: '',
    code: '',
    feature_name: '',
    feature_description: '',
    required_level: 1,
    is_active: true
  });

  // Mock data initialization
  useEffect(() => {
    // Simulate loading VIP plans
    const mockPlans: VipPlan[] = [
      {
        id: 1,
        name: '基础版VIP',
        description: '享受基础VIP特权',
        price: 9.9,
        duration_days: 30,
        level: 1,
        features: JSON.stringify(['高速下载', '无广告体验']),
        is_active: true
      },
      {
        id: 2,
        name: '进阶版VIP',
        description: '享受更多VIP特权',
        price: 19.9,
        duration_days: 30,
        level: 2,
        features: JSON.stringify(['高速下载', '无广告体验', '专属客服']),
        is_active: true
      },
      {
        id: 3,
        name: '专业版VIP',
        description: '享受全部VIP特权',
        price: 29.9,
        duration_days: 30,
        level: 3,
        features: JSON.stringify(['高速下载', '无广告体验', '专属客服', '优先支持']),
        is_active: true
      }
    ];

    // Simulate loading VIP features
    const mockFeatures: VipFeature[] = [
      {
        id: 1,
        code: 'download.speed',
        name: '高速下载',
        description: '享受最高下载速度',
        required_level: 1,
        is_active: true
      },
      {
        id: 2,
        code: 'ad.block',
        name: '无广告体验',
        description: '页面无广告干扰',
        required_level: 1,
        is_active: true
      },
      {
        id: 3,
        code: 'support.priority',
        name: '优先支持',
        description: '优先获得技术支持',
        required_level: 3,
        is_active: true
      }
    ];

    // Simulate loading subscriptions
    const mockSubscriptions: Subscription[] = [
      {
        id: 1,
        user_id: 1001,
        plan_id: 2,
        plan_name: '进阶版VIP',
        starts_at: '2023-01-15T10:30:00Z',
        expires_at: '2023-02-15T10:30:00Z',
        payment_amount: 19.9,
        transaction_id: 'TXN001',
        status: 1
      },
      {
        id: 2,
        user_id: 1002,
        plan_id: 1,
        plan_name: '基础版VIP',
        starts_at: '2023-02-01T14:20:00Z',
        expires_at: '2023-03-01T14:20:00Z',
        payment_amount: 9.9,
        transaction_id: 'TXN002',
        status: 1
      },
      {
        id: 3,
        user_id: 1003,
        plan_id: 3,
        plan_name: '专业版VIP',
        starts_at: '2023-01-20T09:15:00Z',
        expires_at: '2023-02-20T09:15:00Z',
        payment_amount: 29.9,
        transaction_id: 'TXN003',
        status: -1
      }
    ];

    setPlans(mockPlans);
    setFeatures(mockFeatures);
    setSubscriptions(mockSubscriptions);
    setTotalPages(1);
  }, []);

  const handleAddPlan = () => {
    setFormData({
      name: '',
      description: '',
      price: 0,
      duration_days: 30,
      level: 1,
      features: '',
      code: '',
      feature_name: '',
      feature_description: '',
      required_level: 1,
      is_active: true
    });
    setCurrentPlan(null);
    setIsPlanModalOpen(true);
  };

  const handleEditPlan = (plan: VipPlan) => {
    setFormData({
      name: plan.name,
      description: plan.description || '',
      price: plan.price,
      duration_days: plan.duration_days,
      level: plan.level,
      features: plan.features || '',
      code: '',
      feature_name: '',
      feature_description: '',
      required_level: 1,
      is_active: plan.is_active
    });
    setCurrentPlan(plan);
    setIsPlanModalOpen(true);
  };

  const handleDeletePlan = (planId: number, planName: string) => {
    if (confirm(`确定要删除套餐 "${planName}" 吗？`)) {
      setPlans(plans.filter(plan => plan.id !== planId));
      toast.success(`套餐 "${planName}" 已删除`);
    }
  };

  const handleAddFeature = () => {
    setFormData({
      name: '',
      description: '',
      price: 0,
      duration_days: 30,
      level: 1,
      features: '',
      code: '',
      feature_name: '',
      feature_description: '',
      required_level: 1,
      is_active: true
    });
    setCurrentFeature(null);
    setIsFeatureModalOpen(true);
  };

  const handleEditFeature = (feature: VipFeature) => {
    setFormData({
      name: '',
      description: '',
      price: 0,
      duration_days: 30,
      level: 1,
      features: '',
      code: feature.code,
      feature_name: feature.name,
      feature_description: feature.description || '',
      required_level: feature.required_level,
      is_active: feature.is_active
    });
    setCurrentFeature(feature);
    setIsFeatureModalOpen(true);
  };

  const handleDeleteFeature = (featureId: number, featureName: string) => {
    if (confirm(`确定要删除功能 "${featureName}" 吗？`)) {
      setFeatures(features.filter(feature => feature.id !== featureId));
      toast.success(`功能 "${featureName}" 已删除`);
    }
  };

  const handleSavePlan = () => {
    if (currentPlan) {
      // Update existing plan
      setPlans(plans.map(plan => 
        plan.id === currentPlan.id 
          ? { 
              ...plan, 
              name: formData.name, 
              description: formData.description,
              price: formData.price,
              duration_days: formData.duration_days,
              level: formData.level,
              features: formData.features,
              is_active: formData.is_active
            } 
          : plan
      ));
      toast.success('VIP套餐已更新');
    } else {
      // Add new plan
      const newPlan: VipPlan = {
        id: plans.length + 1,
        name: formData.name,
        description: formData.description,
        price: formData.price,
        duration_days: formData.duration_days,
        level: formData.level,
        features: formData.features,
        is_active: formData.is_active
      };
      setPlans([...plans, newPlan]);
      toast.success('VIP套餐已添加');
    }
    
    setIsPlanModalOpen(false);
  };

  const handleSaveFeature = () => {
    if (currentFeature) {
      // Update existing feature
      setFeatures(features.map(feature => 
        feature.id === currentFeature.id 
          ? { 
              ...feature, 
              code: formData.code, 
              name: formData.feature_name,
              description: formData.feature_description,
              required_level: formData.required_level,
              is_active: formData.is_active
            } 
          : feature
      ));
      toast.success('功能特权已更新');
    } else {
      // Add new feature
      const newFeature: VipFeature = {
        id: features.length + 1,
        code: formData.code,
        name: formData.feature_name,
        description: formData.feature_description,
        required_level: formData.required_level,
        is_active: formData.is_active
      };
      setFeatures([...features, newFeature]);
      toast.success('功能特权已添加');
    }
    
    setIsFeatureModalOpen(false);
  };

  const getPlanColor = (level: number) => {
    const colors = {
      1: 'bg-blue-500',
      2: 'bg-purple-500',
      3: 'bg-cyan-500',
      4: 'bg-yellow-500'
    };
    return colors[level as keyof typeof colors] || 'bg-gray-400';
  };

  const getLevelBadgeColor = (level: number) => {
    const colors = {
      1: 'bg-blue-100 text-blue-800',
      2: 'bg-purple-100 text-purple-800',
      3: 'bg-cyan-100 text-cyan-800',
      4: 'bg-yellow-100 text-yellow-800'
    };
    return colors[level as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getStatusColor = (status: number) => {
    const colors = {
      1: 'bg-green-100 text-green-800',
      '-1': 'bg-red-100 text-red-800',
      '10': 'bg-yellow-100 text-yellow-800',
      '-2': 'bg-gray-100 text-gray-800'
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getStatusText = (status: number) => {
    const texts = {
      1: '活跃',
      '-1': '已过期',
      '10': '待支付',
      '-2': '已取消'
    };
    return texts[status as keyof typeof texts] || status.toString();
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '未设置';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredPlans = plans.filter(plan => 
    plan.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plan.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredFeatures = features.filter(feature => 
    feature.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    feature.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredSubscriptions = subscriptions.filter(sub => 
    sub.user_id.toString().includes(searchQuery) ||
    sub.plan_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">VIP管理</h1>
        <p className="text-muted-foreground">管理VIP套餐、订阅和功能特权</p>
      </div>

      {/* Tab Navigation */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'plans' | 'subscriptions' | 'features')}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="plans" className="flex items-center gap-2">
            <Crown className="w-4 h-4" />
            VIP套餐管理
          </TabsTrigger>
          <TabsTrigger value="subscriptions" className="flex items-center gap-2">
            <Receipt className="w-4 h-4" />
            订阅记录
          </TabsTrigger>
          <TabsTrigger value="features" className="flex items-center gap-2">
            <Star className="w-4 h-4" />
            功能特权
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* VIP Plans Content */}
      {activeTab === 'plans' && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>VIP套餐列表</CardTitle>
              <Button onClick={handleAddPlan}>
                <Plus className="w-4 h-4 mr-2" />
                新增套餐
              </Button>
            </CardHeader>
            <CardContent>
              {/* Search and Filter */}
              <div className="flex flex-wrap gap-4 mb-6">
                <div className="flex-1 min-w-[200px]">
                  <Input
                    type="text"
                    placeholder="搜索套餐名称..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <select className="px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent">
                  <option value="">所有状态</option>
                  <option value="active">激活</option>
                  <option value="inactive">未激活</option>
                </select>
                <select className="px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent">
                  <option value="">所有等级</option>
                  <option value="1">等级 1</option>
                  <option value="2">等级 2</option>
                  <option value="3">等级 3</option>
                </select>
              </div>

              {/* Plans Table */}
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>套餐信息</TableHead>
                      <TableHead>价格/时长</TableHead>
                      <TableHead>等级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPlans.map((plan) => (
                      <TableRow key={plan.id}>
                        <TableCell>
                          <div className="flex items-center">
                            <div className={`flex-shrink-0 h-10 w-10 ${getPlanColor(plan.level)} rounded-lg flex items-center justify-center`}>
                              <Crown className="w-4 h-4 text-white" />
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-gray-900">{plan.name}</div>
                              <div className="text-sm text-gray-500">{plan.description || '暂无描述'}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900 font-semibold">¥{plan.price.toFixed(2)}</div>
                          <div className="text-sm text-gray-500">{plan.duration_days} 天</div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getLevelBadgeColor(plan.level)}>
                            等级 {plan.level}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={plan.is_active ? 'default' : 'secondary'}>
                            {plan.is_active ? '激活' : '未激活'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm" onClick={() => handleEditPlan(plan)}>
                              <Edit className="w-4 h-4 mr-1" />
                              编辑
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => handleDeletePlan(plan.id, plan.name)}
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

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-700">
                  显示第 <span className="font-medium">{(currentPage - 1) * 10 + 1}</span> 至
                  <span className="font-medium">{Math.min(currentPage * 10, plans.length)}</span> 条，共
                  <span className="font-medium">{plans.length}</span> 条记录
                </div>
                <div className="flex items-center space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <div className="flex items-center space-x-1">
                    {Array.from({length: totalPages}, (_, i) => i + 1).map(page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </Button>
                    ))}
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Subscriptions Content */}
      {activeTab === 'subscriptions' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>订阅记录</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Search and Filter */}
              <div className="flex flex-wrap gap-4 mb-6">
                <div className="flex-1 min-w-[200px]">
                  <Input
                    type="text"
                    placeholder="搜索用户ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <select className="px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent">
                  <option value="">所有状态</option>
                  <option value="active">活跃</option>
                  <option value="expired">已过期</option>
                  <option value="pending">待支付</option>
                </select>
                <Input type="date" className="px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent" />
              </div>

              {/* Subscriptions Table */}
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>用户信息</TableHead>
                      <TableHead>套餐详情</TableHead>
                      <TableHead>时间信息</TableHead>
                      <TableHead>支付信息</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSubscriptions.map((sub) => (
                      <TableRow key={sub.id}>
                        <TableCell>
                          <div className="text-sm font-medium text-gray-900">用户 #{sub.user_id}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">{sub.plan_name}</div>
                          <div className="text-sm text-gray-500">套餐ID: {sub.plan_id}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">开始: {formatDate(sub.starts_at)}</div>
                          <div className="text-sm text-gray-500">到期: {formatDate(sub.expires_at)}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">¥{sub.payment_amount.toFixed(2)}</div>
                          <div className="text-sm text-gray-500">{sub.transaction_id || '无交易ID'}</div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(sub.status)}>
                            {getStatusText(sub.status)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button variant="outline" size="sm">
                            <Edit className="w-4 h-4 mr-1" />
                            编辑
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-700">
                  显示第 <span className="font-medium">{(currentPage - 1) * 10 + 1}</span> 至
                  <span className="font-medium">{Math.min(currentPage * 10, subscriptions.length)}</span> 条，共
                  <span className="font-medium">{subscriptions.length}</span> 条记录
                </div>
                <div className="flex items-center space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <div className="flex items-center space-x-1">
                    {Array.from({length: totalPages}, (_, i) => i + 1).map(page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </Button>
                    ))}
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Features Content */}
      {activeTab === 'features' && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>功能特权管理</CardTitle>
              <Button onClick={handleAddFeature}>
                <Plus className="w-4 h-4 mr-2" />
                新增功能
              </Button>
            </CardHeader>
            <CardContent>
              {/* Features Table */}
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>功能代码</TableHead>
                      <TableHead>功能名称</TableHead>
                      <TableHead>所需等级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFeatures.map((feature) => (
                      <TableRow key={feature.id}>
                        <TableCell>
                          <div className="text-sm font-medium text-gray-900">{feature.code}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">{feature.name}</div>
                          <div className="text-sm text-gray-500">{feature.description || '暂无描述'}</div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getLevelBadgeColor(feature.required_level)}>
                            等级 {feature.required_level}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={feature.is_active ? 'default' : 'secondary'}>
                            {feature.is_active ? '激活' : '未激活'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button variant="outline" size="sm" onClick={() => handleEditFeature(feature)}>
                              <Edit className="w-4 h-4 mr-1" />
                              编辑
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => handleDeleteFeature(feature.id, feature.name)}
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

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-700">
                  显示第 <span className="font-medium">{(currentPage - 1) * 10 + 1}</span> 至
                  <span className="font-medium">{Math.min(currentPage * 10, features.length)}</span> 条，共
                  <span className="font-medium">{features.length}</span> 条记录
                </div>
                <div className="flex items-center space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <div className="flex items-center space-x-1">
                    {Array.from({length: totalPages}, (_, i) => i + 1).map(page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </Button>
                    ))}
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* VIP Plan Modal */}
      <Dialog open={isPlanModalOpen} onOpenChange={setIsPlanModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {currentPlan ? '编辑VIP套餐' : '新增VIP套餐'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={(e) => { e.preventDefault(); handleSavePlan(); }}>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="plan-name">套餐名称</Label>
                  <Input
                    id="plan-name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="plan-price">价格 (¥)</Label>
                  <Input
                    id="plan-price"
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) => setFormData({...formData, price: parseFloat(e.target.value) || 0})}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="plan-duration">有效期 (天)</Label>
                  <Input
                    id="plan-duration"
                    type="number"
                    value={formData.duration_days}
                    onChange={(e) => setFormData({...formData, duration_days: parseInt(e.target.value) || 30})}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="plan-level">VIP等级</Label>
                  <select
                    id="plan-level"
                    value={formData.level}
                    onChange={(e) => setFormData({...formData, level: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                    required
                  >
                    <option value="1">等级 1 - 基础版</option>
                    <option value="2">等级 2 - 进阶版</option>
                    <option value="3">等级 3 - 专业版</option>
                    <option value="4">等级 4 - 尊享版</option>
                  </select>
                </div>
              </div>
              <div>
                <Label htmlFor="plan-description">套餐描述</Label>
                <Input
                  id="plan-description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="plan-features">特权功能 (JSON格式)</Label>
                <Input
                  id="plan-features"
                  value={formData.features}
                  onChange={(e) => setFormData({...formData, features: e.target.value})}
                  placeholder='示例: ["高速下载", "无广告体验"]'
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="plan-active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                  className="rounded border-input text-primary focus:ring-primary"
                />
                <Label htmlFor="plan-active" className="ml-2">激活套餐</Label>
              </div>
            </div>
            
            <DialogFooter className="flex sm:justify-between">
              <Button 
                type="button" 
                variant="outline"
                onClick={() => setIsPlanModalOpen(false)}
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

      {/* Feature Modal */}
      <Dialog open={isFeatureModalOpen} onOpenChange={setIsFeatureModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {currentFeature ? '编辑功能特权' : '新增功能特权'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={(e) => { e.preventDefault(); handleSaveFeature(); }}>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="feature-code">功能代码</Label>
                <Input
                  id="feature-code"
                  value={formData.code}
                  onChange={(e) => setFormData({...formData, code: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label htmlFor="feature-name">功能名称</Label>
                <Input
                  id="feature-name"
                  value={formData.feature_name}
                  onChange={(e) => setFormData({...formData, feature_name: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label htmlFor="feature-description">功能描述</Label>
                <Input
                  id="feature-description"
                  value={formData.feature_description}
                  onChange={(e) => setFormData({...formData, feature_description: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="feature-level">所需等级</Label>
                <select
                  id="feature-level"
                  value={formData.required_level}
                  onChange={(e) => setFormData({...formData, required_level: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  required
                >
                  <option value="1">等级 1</option>
                  <option value="2">等级 2</option>
                  <option value="3">等级 3</option>
                  <option value="4">等级 4</option>
                </select>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="feature-active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                  className="rounded border-input text-primary focus:ring-primary"
                />
                <Label htmlFor="feature-active" className="ml-2">激活功能</Label>
              </div>
            </div>
            
            <DialogFooter className="flex sm:justify-between">
              <Button 
                type="button" 
                variant="outline"
                onClick={() => setIsFeatureModalOpen(false)}
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