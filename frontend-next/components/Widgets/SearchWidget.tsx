/**
 * 搜索框Widget
 */

'use client';

import React, {useState} from 'react';
import {useRouter} from 'next/navigation';
import {Search} from 'lucide-react';
import {Input} from '@/components/ui/input';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';

interface SearchWidgetProps {
    widgetId: number;
    title: string;
    config: {
        placeholder?: string;
    };
}

const SearchWidget: React.FC<SearchWidgetProps> = ({title, config}) => {
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchQuery.trim()) {
            router.push(`/articles?search=${encodeURIComponent(searchQuery)}`);
        }
    };

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg">{title}</CardTitle>
                </CardHeader>
            )}
            <CardContent>
                <form onSubmit={handleSearch} className="flex gap-2">
                    <Input
                        type="search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder={config.placeholder || '搜索文章...'}
                        className="flex-1"
                    />
                    <Button type="submit" size="icon">
                        <Search className="w-4 h-4"/>
                    </Button>
                </form>
            </CardContent>
        </Card>
    );
};

export default SearchWidget;
