'use client';

import React from 'react';
import {Label} from '@/components/ui/label';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Switch} from '@/components/ui/switch';

interface BaseInputFieldProps {
  label: string;
  description?: string;
  className?: string;
}

interface TextInputFieldProps extends BaseInputFieldProps {
  type?: 'text' | 'number' | 'email' | 'password' | 'url';
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  min?: number;
  max?: number;
}

interface TextareaInputFieldProps extends BaseInputFieldProps {
  type: 'textarea';
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}

interface SelectInputFieldProps extends BaseInputFieldProps {
  type: 'select';
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}

interface BooleanInputFieldProps extends BaseInputFieldProps {
  type: 'boolean';
  value: boolean;
  onChange: (value: boolean) => void;
}

type InputFieldProps = 
  | TextInputFieldProps 
  | TextareaInputFieldProps 
  | SelectInputFieldProps 
  | BooleanInputFieldProps;

const InputField: React.FC<InputFieldProps> = (props) => {
  const renderInput = () => {
    switch (props.type) {
      case 'textarea':
        return (
          <Textarea
            value={props.value}
            onChange={(e) => props.onChange(e.target.value)}
            placeholder={props.placeholder}
            rows={props.rows || 3}
          />
        );
      case 'select':
        return (
          <Select value={props.value} onValueChange={props.onChange}>
            <SelectTrigger>
              <SelectValue placeholder={props.placeholder} />
            </SelectTrigger>
            <SelectContent>
              {props.options.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <Switch
              checked={props.value}
              onCheckedChange={props.onChange}
            />
            <span className="text-sm text-gray-500">
              {props.value ? '开启' : '关闭'}
            </span>
          </div>
        );
      default: // text, number, email, password, url
        return (
          <Input
            type={props.type || 'text'}
            value={props.value}
            onChange={(e) => props.onChange(e.target.value)}
            placeholder={props.placeholder}
            min={props.min}
            max={props.max}
          />
        );
    }
  };

  return (
    <div className={`space-y-2 ${props.className || ''}`}>
      <div className="space-y-1">
        <Label>{props.label}</Label>
        {props.description && (
          <p className="text-sm text-gray-500">{props.description}</p>
        )}
      </div>
      {renderInput()}
    </div>
  );
};

export default InputField;