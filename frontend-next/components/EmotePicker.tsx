'use client';

import React, {useState} from 'react';
import {getAvailableEmotes} from '@/lib/emoteService';
import {Button} from '@/components/ui/button';
import {Popover, PopoverContent, PopoverTrigger} from '@/components/ui/popover';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Smile} from 'lucide-react';

interface EmotePickerProps {
  onSelect: (emoteCode: string) => void;
  trigger?: React.ReactNode;
}

export function EmotePicker({onSelect, trigger}: EmotePickerProps) {
  const [open, setOpen] = useState(false);
  const emotes = getAvailableEmotes();
  
  // 按分类分组
  const categorizedEmotes = emotes.reduce((acc, emote) => {
    if (!acc[emote.category]) {
      acc[emote.category] = [];
    }
    acc[emote.category].push(emote);
    return acc;
  }, {} as Record<string, typeof emotes>);

  const categories = Object.keys(categorizedEmotes);

  const handleSelect = (code: string) => {
    onSelect(code);
    setOpen(false);
  };

  return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          {trigger || (
              <Button variant="ghost" size="sm" type="button">
                <Smile className="w-5 h-5"/>
              </Button>
          )}
        </PopoverTrigger>
        <PopoverContent className="w-80 p-2" align="start">
          <Tabs defaultValue={categories[0]} className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-2">
              {categories.map((category) => (
                  <TabsTrigger key={category} value={category} className="text-xs">
                    {category}
                  </TabsTrigger>
              ))}
            </TabsList>

            {categories.map((category) => (
                <TabsContent key={category} value={category} className="mt-0">
                  <div className="grid grid-cols-6 gap-1 max-h-48 overflow-y-auto p-1">
                    {categorizedEmotes[category].map((emote) => (
                        <Button
                            key={emote.code}
                            variant="ghost"
                            size="sm"
                            className="h-9 w-9 p-0 hover:bg-gray-100 dark:hover:bg-gray-800 text-lg"
                            onClick={() => handleSelect(emote.code)}
                            title={emote.code}
                        >
                          {emote.emoji}
                        </Button>
                    ))}
                  </div>
                </TabsContent>
            ))}
          </Tabs>
        </PopoverContent>
      </Popover>
  );
}
