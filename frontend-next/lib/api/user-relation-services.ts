import {apiClient, ApiResponse} from "@/app/lib/api";

// User relation types
export interface UserRelation {
    id: number;
    username: string;
    email: string;
    bio?: string;
    profile_picture?: string;
}

export interface RelationWithDate {
    user: UserRelation;
    created_at: string;
}

export interface FollowToggleResponse {
    message: string;
}

export interface UserListResponse {
    users: UserRelation[];
    following_ids: number[];
}

export interface RelationCounts {
    fans_count: number;
    following_count: number;
}

export interface RelationListResponse {
    fans_list: RelationWithDate[];
    fans_count: number;
    following_list: RelationWithDate[];
    following_count: number;
}

export class RelationService {
    static async getFollowers(): Promise<ApiResponse<RelationListResponse>> {
        return apiClient.get('/relations/followers');
    }

    static async getFollowing(): Promise<ApiResponse<RelationListResponse>> {
        return apiClient.get('/relations/following');
    }

    static async getUsers(): Promise<ApiResponse<UserListResponse>> {
        return apiClient.get('/relations/users');
    }

    static async followUser(targetUserId: number): Promise<ApiResponse<FollowToggleResponse>> {
        return apiClient.post(`/relations/follow/${targetUserId}`);
    }

    static async unfollowUser(targetUserId: number): Promise<ApiResponse<FollowToggleResponse>> {
        return apiClient.post(`/relations/unfollow/${targetUserId}`);
    }
}
