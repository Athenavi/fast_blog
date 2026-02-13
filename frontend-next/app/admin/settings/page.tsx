'use client';

import React, {useEffect, useState} from 'react';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Card} from '@/components/ui/card';
import {FileText, Home, Loader2, Menu, Settings} from 'lucide-react';
import GeneralSettingsTab from './components/GeneralSettingsTab';
import HomeConfigTab from './components/HomeConfigTab';
import MenuManagementTab from './components/MenuManagementTab';
import PageManagementTab from './components/PageManagementTab';
import MenuModal from './components/MenuModal';
import MenuItemModal from './components/MenuItemModal';
import PageModal from './components/PageModal';
import DeleteConfirmationModal from './components/DeleteConfirmationModal';
import {
    AdminSettingsService,
    Menu as MenuType,
    MenuItem as MenuItemType,
    Page as PageType
} from '@/lib/api/admin-settings-service';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [homeConfig, setHomeConfig] = useState<Record<string, string>>({});
  const [menus, setMenus] = useState<MenuType[]>([]);
  const [menuItems, setMenuItems] = useState<Record<string, MenuItemType[]>>({});
  const [pages, setPages] = useState<PageType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Modal states
  const [menuModalOpen, setMenuModalOpen] = useState(false);
  const [menuItemModalOpen, setMenuItemModalOpen] = useState(false);
  const [pageModalOpen, setPageModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteModalType, setDeleteModalType] = useState<'menu' | 'menuItem' | 'page'>('menu');
  const [itemToDelete, setItemToDelete] = useState<number | null>(null);
  
  // Selected items for editing
  const [selectedMenu, setSelectedMenu] = useState<MenuType | null>(null);
  const [selectedMenuItem, setSelectedMenuItem] = useState<MenuItemType | null>(null);
  const [selectedPage, setSelectedPage] = useState<PageType | null>(null);

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await AdminSettingsService.getSettings();
      
      if (response.success && response.data) {
        setSettings(response.data.settings);
        // Extract home config from settings
        const homeConfigKeys = Object.keys(response.data.settings).filter(key => 
          key.startsWith('home_') || 
          key.startsWith('hero_') || 
          key.startsWith('featured_') || 
          key.includes('_title') || 
          key.includes('_subtitle') || 
          key.includes('_cta_') || 
          key.includes('_count') || 
          key.includes('_background') || 
          key.includes('_empty_') || 
          key.includes('_newsletter_') || 
          key.includes('_filter_')
        );
        const extractedHomeConfig: Record<string, string> = {};
        homeConfigKeys.forEach(key => {
          extractedHomeConfig[key] = response.data?.settings[key] || '';
        });
        setHomeConfig(extractedHomeConfig);
        
        setMenus(response.data.menus || []);
        setMenuItems(response.data.menu_items || {});
        setPages(response.data.pages || []);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handlers for general settings
  const handleSettingChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveGeneralSettings = async () => {
    setSaving(true);
    try {
      const response = await AdminSettingsService.updateSettings(settings);
      if (!response.success) {
        throw new Error(response.message || '保存失败');
      }
      // Optionally show success message
    } catch (error) {
      console.error('Failed to save settings:', error);
      // Optionally show error message
    } finally {
      setSaving(false);
    }
  };

  // Handlers for home config
  const handleHomeConfigChange = (key: string, value: string) => {
    setHomeConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveHomeConfig = async () => {
    setSaving(true);
    try {
      // Combine home config with existing settings
      const updatedSettings = { ...settings, ...homeConfig };
      const response = await AdminSettingsService.updateSettings(updatedSettings);
      if (!response.success) {
        throw new Error(response.message || '保存失败');
      }
      // Optionally show success message
    } catch (error) {
      console.error('Failed to save home config:', error);
      // Optionally show error message
    } finally {
      setSaving(false);
    }
  };

  // Handlers for menu management
  const handleAddMenu = () => {
    setSelectedMenu(null);
    setMenuModalOpen(true);
  };

  const handleEditMenu = (menu: MenuType) => {
    setSelectedMenu(menu);
    setMenuModalOpen(true);
  };

  const handleSaveMenu = async (menu: MenuType) => {
    setSaving(true);
    try {
      let response;
      if (menu.id) {
        // Update existing menu
        response = await AdminSettingsService.updateMenu(menu.id, menu);
      } else {
        // Create new menu
        const newMenu = {
          name: menu.name,
          slug: menu.slug,
          description: menu.description,
          is_active: menu.is_active
        };
        response = await AdminSettingsService.createMenu(newMenu);
      }
      
      if (!response.success) {
        throw new Error(response.message || '保存菜单失败');
      }
      
      await loadData(); // Refresh data
    } catch (error) {
      console.error('Failed to save menu:', error);
    } finally {
      setSaving(false);
      setMenuModalOpen(false);
    }
  };

  const handleDeleteMenu = (menuId: number) => {
    setDeleteModalType('menu');
    setItemToDelete(menuId);
    setDeleteModalOpen(true);
  };

  const confirmDeleteMenu = async () => {
    if (itemToDelete !== null) {
      try {
        const response = await AdminSettingsService.deleteMenu(itemToDelete);
        if (!response.success) {
          throw new Error(response.message || '删除菜单失败');
        }
        await loadData(); // Refresh data
      } catch (error) {
        console.error('Failed to delete menu:', error);
      } finally {
        setDeleteModalOpen(false);
        setItemToDelete(null);
      }
    }
  };

  const handleAddMenuItem = (menu: MenuType) => {
    setSelectedMenuItem({ 
      id: 0, // 使用 0 作为新项目标识
      title: '',
      url: '',
      target: '_self',
      order_index: 0,
      parent_id: undefined,
      menu_id: menu.id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_active: true
    });
    setMenuItemModalOpen(true);
  };

  const handleEditMenuItem = (item: MenuItemType) => {
    setSelectedMenuItem(item);
    setMenuItemModalOpen(true);
  };

  const handleSaveMenuItem = async (item: MenuItemType) => {
    setSaving(true);
    try {
      let response;
      if (item.id) {
        // Update existing menu item
        response = await AdminSettingsService.updateMenuItem(item.id, item);
      } else {
        // Create new menu item
        const newItem = {
          title: item.title,
          url: item.url,
          target: item.target,
          order_index: item.order_index,
          parent_id: item.parent_id,
          menu_id: item.menu_id,
          is_active: item.is_active
        };
        response = await AdminSettingsService.createMenuItem(newItem);
      }
      
      if (!response.success) {
        throw new Error(response.message || '保存菜单项失败');
      }
      
      await loadData(); // Refresh data
    } catch (error) {
      console.error('Failed to save menu item:', error);
    } finally {
      setSaving(false);
      setMenuItemModalOpen(false);
    }
  };

  const handleDeleteMenuItem = (itemId: number) => {
    setDeleteModalType('menuItem');
    setItemToDelete(itemId);
    setDeleteModalOpen(true);
  };

  const confirmDeleteMenuItem = async () => {
    if (itemToDelete !== null) {
      try {
        const response = await AdminSettingsService.deleteMenuItem(itemToDelete);
        if (!response.success) {
          throw new Error(response.message || '删除菜单项失败');
        }
        await loadData(); // Refresh data
      } catch (error) {
        console.error('Failed to delete menu item:', error);
      } finally {
        setDeleteModalOpen(false);
        setItemToDelete(null);
      }
    }
  };

  // Handlers for page management
  const handleAddPage = () => {
    setSelectedPage(null);
    setPageModalOpen(true);
  };

  const handleEditPage = (page: PageType) => {
    setSelectedPage(page);
    setPageModalOpen(true);
  };

  const handleSavePage = async (page: PageType) => {
    setSaving(true);
    try {
      let response;
      if (page.id) {
        // Update existing page
        response = await AdminSettingsService.updatePage(page.id, page);
      } else {
        // Create new page
        const newPage = {
          title: page.title,
          slug: page.slug,
          content: page.content,
          excerpt: page.excerpt,
          template: page.template,
          status: page.status,
          parent_id: page.parent_id,
          order_index: page.order_index,
          meta_title: page.meta_title,
          meta_description: page.meta_description,
          meta_keywords: page.meta_keywords
        };
        response = await AdminSettingsService.createPage(newPage);
      }
      
      if (!response.success) {
        throw new Error(response.message || '保存页面失败');
      }
      
      await loadData(); // Refresh data
    } catch (error) {
      console.error('Failed to save page:', error);
    } finally {
      setSaving(false);
      setPageModalOpen(false);
    }
  };

  const handleDeletePage = (pageId: number) => {
    setDeleteModalType('page');
    setItemToDelete(pageId);
    setDeleteModalOpen(true);
  };

  const confirmDeletePage = async () => {
    if (itemToDelete !== null) {
      try {
        const response = await AdminSettingsService.deletePage(itemToDelete);
        if (!response.success) {
          throw new Error(response.message || '删除页面失败');
        }
        await loadData(); // Refresh data
      } catch (error) {
        console.error('Failed to delete page:', error);
      } finally {
        setDeleteModalOpen(false);
        setItemToDelete(null);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">站点设置</h1>
        <p className="text-gray-500 mt-2">管理您的站点配置、菜单和页面</p>
      </div>

      <Card className="p-0 shadow-none border-0">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 lg:grid-cols-4 bg-gray-100 p-1 mb-6">
            <TabsTrigger value="general" className="data-[state=active]:bg-white data-[state=active]:shadow-sm flex items-center gap-2">
              <Settings className="w-4 h-4" />
              常规设置
            </TabsTrigger>
            <TabsTrigger value="home" className="data-[state=active]:bg-white data-[state=active]:shadow-sm flex items-center gap-2">
              <Home className="w-4 h-4" />
              首页配置
            </TabsTrigger>
            <TabsTrigger value="menu" className="data-[state=active]:bg-white data-[state=active]:shadow-sm flex items-center gap-2">
              <Menu className="w-4 h-4" />
              菜单管理
            </TabsTrigger>
            <TabsTrigger value="pages" className="data-[state=active]:bg-white data-[state=active]:shadow-sm flex items-center gap-2">
              <FileText className="w-4 h-4" />
              页面管理
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="m-0">
            <GeneralSettingsTab 
              settings={settings} 
              handleSettingChange={handleSettingChange}
              handleSaveGeneralSettings={handleSaveGeneralSettings}
            />
          </TabsContent>

          <TabsContent value="home" className="m-0">
            <HomeConfigTab 
              homeConfig={homeConfig} 
              handleHomeConfigChange={handleHomeConfigChange}
              handleSaveHomeConfig={handleSaveHomeConfig}
              homeConfigLoading={saving}
            />
          </TabsContent>

          <TabsContent value="menu" className="m-0">
            <MenuManagementTab 
              menus={menus} 
              menuItems={menuItems}
              onAddMenu={handleAddMenu}
              onEditMenu={handleEditMenu}
              onDeleteMenu={handleDeleteMenu}
              onAddMenuItem={handleAddMenuItem}
              onEditMenuItem={handleEditMenuItem}
              onDeleteMenuItem={handleDeleteMenuItem}
            />
          </TabsContent>

          <TabsContent value="pages" className="m-0">
            <PageManagementTab 
              pages={pages} 
              onAddPage={handleAddPage}
              onEditPage={handleEditPage}
              onDeletePage={handleDeletePage}
            />
          </TabsContent>
        </Tabs>
      </Card>

      {/* Modals */}
      <MenuModal
        open={menuModalOpen}
        onOpenChange={setMenuModalOpen}
        menu={selectedMenu || undefined}
        onSave={handleSaveMenu}
      />

      <MenuItemModal
        open={menuItemModalOpen}
        onOpenChange={setMenuItemModalOpen}
        menuItem={selectedMenuItem || undefined}
        menus={menus}
        onSave={handleSaveMenuItem}
      />

      <PageModal
        open={pageModalOpen}
        onOpenChange={setPageModalOpen}
        page={selectedPage || undefined}
        onSave={handleSavePage}
      />

      <DeleteConfirmationModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        type={deleteModalType}
        onConfirm={
          deleteModalType === 'menu' ? confirmDeleteMenu :
          deleteModalType === 'menuItem' ? confirmDeleteMenuItem :
          confirmDeletePage
        }
      />
    </div>
  );
};

export default SettingsPage;