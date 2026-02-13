// Backup management types
import {ApiResponse} from "@/lib/api/base-types";
import {apiClient} from "@/app/lib/api";

export interface BackupFile {
    name: string;
    type: 'schema' | 'data' | 'all' | 'unknown';
    size: number;
    created_at: string;
}

// Backup management service
export class BackupService {
    static async getBackups(): Promise<ApiResponse<{ data: BackupFile[] }>> {
        return apiClient.get('/backup/list');
    }

    static async createBackup(type: 'schema' | 'data' | 'all'): Promise<ApiResponse<{
        message: string;
        filename: string
    }>> {
        return apiClient.post('/backup/create', {backup_type: type});
    }

    static async deleteBackup(filename: string): Promise<ApiResponse<{ message: string }>> {
        return apiClient.post('/backup/delete', {filename});
    }

    static async downloadBackup(filename: string): Promise<Blob> {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
        const response = await fetch(`${baseUrl}/backup/download/${filename}`, {
            method: 'GET',
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error(`Download failed: ${response.statusText}`);
        }

        return response.blob();
    }
}