'use client';

import React from 'react';
import {Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';

interface SettingCardProps {
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

const SettingCard: React.FC<SettingCardProps> = ({
  title,
  description,
  children,
  footer,
  className = ''
}) => {
  return (
    <Card className={`overflow-hidden ${className}`}>
      <CardHeader className="border-b">
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="p-6">
        <div className="space-y-4">
          {children}
        </div>
      </CardContent>
      {footer && (
        <>
          <Separator />
          <CardFooter className="p-6">
            {footer}
          </CardFooter>
        </>
      )}
    </Card>
  );
};

export default SettingCard;