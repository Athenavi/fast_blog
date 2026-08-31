import type {ApiResponse} from '@/lib/api/base-types';
import {apiClient} from './base-client';
import {MEMBERSHIP} from './api-paths';

export interface PremiumArticle {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    views: number;
    likes: number;
    required_vip_level: number;
    created_at?: string;
    updated_at?: string;
    user_id: number;
    category_id: number;
}

export interface PremiumContentResponse {
    active_status: {
        is_vip: boolean;
        level: number;
        expires_at: string | null;
        plan_name: string | null;
    };
    current_vip_level: number;
    articles: PremiumArticle[];
    total?: number;
    page?: number;
    page_size?: number;
}

// VIP types
export interface VIPPlan {
    id: number;
    name: string;
    description?: string;
    price: number;
    original_price?: number;
    duration_days: number;
    level: number;
    features?: string;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface VIPFeature {
    id: number;
    code: string;
    name: string;
    description?: string;
    required_level: number;
    is_active: boolean;
    created_at?: string;
}

export interface VIPSubscription {
    id: number;
    user_id: number;
    plan_id: number;
    plan_name?: string;
    level?: number;
    starts_at: string;
    expires_at: string;
    status: number;
    payment_amount?: number;
    transaction_id?: string;
    created_at?: string;
}

export interface VIPPlansResponse {
    plans: VIPPlan[];
    features: VIPFeature[];
}

export interface VIPFeaturesResponse {
    features_by_level: Record<number, VIPFeature[]>;
    features: VIPFeature[];
}

export interface MyVipSubscriptionResponse {
    active_subscription?: VIPSubscription;
    subscription_history: VIPSubscription[];
}

// VIP service
export class VIPService {
    static async getVipPlans(): Promise<ApiResponse<VIPPlan[]>> {
        return apiClient.get(MEMBERSHIP.PLANS);
    }

    static async getVipFeatures(): Promise<ApiResponse<VIPFeaturesResponse>> {
        return apiClient.get(MEMBERSHIP.FEATURES);
    }

    static async getMySubscription(): Promise<ApiResponse<MyVipSubscriptionResponse>> {
        return apiClient.get(MEMBERSHIP.MY_SUBSCRIPTION);
    }

    static async getPremiumContent(): Promise<ApiResponse<PremiumContentResponse>> {
        return apiClient.get(MEMBERSHIP.PREMIUM_CONTENT);
    }

    static async getVipStatus(): Promise<ApiResponse<any>> {
        return apiClient.get(MEMBERSHIP.STATUS);
    }

    static async checkContentAccess(articleId: number, requiredLevel: number = 0): Promise<ApiResponse<any>> {
        return apiClient.get(MEMBERSHIP.CHECK_ACCESS, {article_id: articleId, required_level: requiredLevel});
    }

    static async subscribe(planId: number, paymentAmount: number = 0, transactionId?: string): Promise<ApiResponse<any>> {
        return apiClient.post(MEMBERSHIP.SUBSCRIBE, {
            plan_id: planId,
            payment_amount: paymentAmount,
            transaction_id: transactionId || null,
        });
    }
}


// Payment types
export interface CreatePaymentRequest {
    user_id: number;
    plan_id: number;
    payment_method: 'alipay' | 'wechat';
}

export interface PaymentData {
    pay_url?: string;
    qr_code?: string;
    order_id: string;
    amount: number;
    description: string;
}

export interface CreatePaymentResponse {
    payment_data: PaymentData;
}

// Payment service
export class PaymentService {
    static async createPayment(data: CreatePaymentRequest): Promise<ApiResponse<CreatePaymentResponse>> {
        return apiClient.post(MEMBERSHIP.SUBSCRIBE, {
            plan_id: data.plan_id,
            payment_amount: 0,
            transaction_id: null,
        });
    }
}
