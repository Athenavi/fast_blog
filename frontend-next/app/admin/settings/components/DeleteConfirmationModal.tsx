import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';

interface DeleteConfirmationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: 'menu' | 'menuItem' | 'page';
  onConfirm: () => void;
}

const DeleteConfirmationModal: React.FC<DeleteConfirmationModalProps> = ({ 
  open, 
  onOpenChange, 
  type, 
  onConfirm 
}) => {
  const getTitle = () => {
    switch (type) {
      case 'menu':
        return '删除菜单';
      case 'menuItem':
        return '删除菜单项';
      case 'page':
        return '删除页面';
      default:
        return '删除确认';
    }
  };

  const getDescription = () => {
    switch (type) {
      case 'menu':
        return '您确定要删除这个菜单吗？此操作将同时删除该菜单下的所有菜单项，且不可逆转。';
      case 'menuItem':
        return '您确定要删除这个菜单项吗？此操作不可逆转。';
      case 'page':
        return '您确定要删除这个页面吗？此操作不可逆转。';
      default:
        return '您确定要执行此删除操作吗？此操作不可逆转。';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{getTitle()}</DialogTitle>
          <DialogDescription>
            {getDescription()}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button variant="destructive" onClick={() => {
            onConfirm();
            onOpenChange(false);
          }}>确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteConfirmationModal;