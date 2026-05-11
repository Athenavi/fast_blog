import CustomBlockManager from '@/components/CustomBlockManager';

export default function CustomBlocksPage() {
    return (
        <div className="container mx-auto py-8 px-4">
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">自定义块管理</h1>
                <p className="text-gray-600 dark:text-gray-400">
                    管理和扩展块编辑器的自定义块类型
                </p>
            </div>

            <CustomBlockManager/>
        </div>
    );
}
