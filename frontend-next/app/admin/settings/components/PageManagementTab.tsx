'use client';

import React from 'react';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Page} from '@/lib/api/admin-settings-service';
import {Edit, ExternalLink, Plus, Trash2} from 'lucide-react';

interface PageManagementTabProps {
  pages: Page[];
  onAddPage: () => void;
  onEditPage: (page: Page) => void;
  onDeletePage: (pageId: number) => void;
}

const PageManagementTab: React.FC<PageManagementTabProps> = ({ 
  pages, 
  onAddPage,
  onEditPage,
  onDeletePage
}) => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">页面管理</h3>
        <Button onClick={onAddPage} className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          新建页面
        </Button>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>页面标题</TableHead>
              <TableHead>URL</TableHead>
              <TableHead>模板</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>更新时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pages.length > 0 ? (
              pages.map((page) => (
                <TableRow key={page.id} className="hover:bg-gray-50">
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <span>{page.title}</span>
                      {page.is_sticky && (
                        <Badge variant="secondary" className="text-xs">置顶</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded break-all">
                      /{page.slug}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{page.template}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={page.status === 1 ? 'default' : 'secondary'}>
                      {page.status === 1 ? '已发布' : '草稿'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {page.updated_at ? new Date(page.updated_at).toLocaleDateString() : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => {
                          window.open(`/${page.slug}`, '_blank');
                        }}
                        className="p-2"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => onEditPage(page)}
                        className="p-2"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => onDeletePage(page.id)}
                        className="p-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  还没有创建任何页面，点击上方按钮创建一个新页面
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default PageManagementTab;