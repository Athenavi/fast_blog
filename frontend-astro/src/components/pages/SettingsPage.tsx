'use client';

import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import SettingsPage from './SettingsPage/index';

export default function SettingsPageGuard() {
  return <AuthGuard><QueryProvider><SettingsPage/></QueryProvider></AuthGuard>;
}

export {default as SettingsPage} from './SettingsPage/index';
