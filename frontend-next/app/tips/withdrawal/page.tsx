'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {useToast} from '@/hooks/use-toast';
import {BalanceInfo, TippingService, WithdrawalRecord} from '@/lib/api/tipping-service';

export default function WithdrawalPage() {
    const {toast} = useToast();
    const [balance, setBalance] = useState<BalanceInfo | null>(null);
    const [withdrawals, setWithdrawals] = useState<WithdrawalRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [withdrawalAmount, setWithdrawalAmount] = useState('');
    const [paymentMethod, setPaymentMethod] = useState('bank_transfer');
    const [accountInfo, setAccountInfo] = useState({
        bank_name: '',
        account_number: '',
        account_holder: '',
    });

    // 加载余额和提现记录
    useEffect(() => {
        loadBalance();
        loadWithdrawals();
    }, []);

    const loadBalance = async () => {
        try {
            const response = await TippingService.getBalance();
            if (response.success && response.data) {
                setBalance(response.data);
            }
        } catch (error) {
            console.error('Failed to load balance:', error);
            toast({
                title: '错误',
                description: '加载余额失败',
                variant: 'destructive',
            });
        }
    };

    const loadWithdrawals = async () => {
        try {
            const response = await TippingService.getMyWithdrawals(50);
            if (response.success && response.data) {
                setWithdrawals(response.data.withdrawals || []);
            }
        } catch (error) {
            console.error('Failed to load withdrawals:', error);
        }
    };

    const handleWithdrawal = async () => {
        const amount = parseFloat(withdrawalAmount);

        // 验证
        if (!amount || amount <= 0) {
            toast({
                title: '错误',
                description: '请输入有效的提现金额',
                variant: 'destructive',
            });
            return;
        }

        if (balance && amount < balance.min_withdrawal_amount) {
            toast({
                title: '错误',
                description: `最低提现金额为 ${balance.min_withdrawal_amount} 元`,
                variant: 'destructive',
            });
            return;
        }

        if (balance && amount > balance.available_balance) {
            toast({
                title: '错误',
                description: '提现金额超过可用余额',
                variant: 'destructive',
            });
            return;
        }

        setLoading(true);
        try {
            const response = await TippingService.requestWithdrawal(amount, paymentMethod, accountInfo);

            if (response.success) {
                toast({
                    title: '成功',
                    description: '提现申请已提交，请等待审核',
                });
                setWithdrawalAmount('');
                loadBalance();
                loadWithdrawals();
            } else {
                toast({
                    title: '错误',
                    description: response.error || '提现申请失败',
                    variant: 'destructive',
                });
            }
        } catch (error) {
            console.error('Withdrawal failed:', error);
            toast({
                title: '错误',
                description: '提现申请失败，请稍后重试',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, {
            label: string;
            variant: 'default' | 'secondary' | 'destructive' | 'outline'
        }> = {
            pending: {label: '待审核', variant: 'secondary'},
            processing: {label: '处理中', variant: 'default'},
            completed: {label: '已完成', variant: 'default'},
            rejected: {label: '已拒绝', variant: 'destructive'},
            cancelled: {label: '已取消', variant: 'outline'},
        };

        const config = statusMap[status] || {label: status, variant: 'outline'};
        return <Badge variant={config.variant}>{config.label}</Badge>;
    };

    const getPaymentMethodLabel = (method: string) => {
        const labels: Record<string, string> = {
            bank_transfer: '银行转账',
            wechat: '微信',
            alipay: '支付宝',
        };
        return labels[method] || method;
    };

    return (
        <div className="container mx-auto py-8 px-4">
            <h1 className="text-3xl font-bold mb-8">提现管理</h1>

            <Tabs defaultValue="withdraw" className="space-y-6">
                <TabsList className="grid w-full max-w-md grid-cols-2">
                    <TabsTrigger value="withdraw">申请提现</TabsTrigger>
                    <TabsTrigger value="history">提现记录</TabsTrigger>
                </TabsList>

                {/* 申请提现 */}
                <TabsContent value="withdraw" className="space-y-6">
                    {/* 余额卡片 */}
                    {balance && (
                        <Card>
                            <CardHeader>
                                <CardTitle>账户余额</CardTitle>
                                <CardDescription>查看您的可提现余额信息</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground">累计收入</p>
                                        <p className="text-2xl font-bold">¥{balance.total_earned.toFixed(2)}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">已提现</p>
                                        <p className="text-2xl font-bold">¥{balance.total_withdrawn.toFixed(2)}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">提现中</p>
                                        <p className="text-2xl font-bold">¥{balance.pending_withdrawal.toFixed(2)}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">可用余额</p>
                                        <p className="text-2xl font-bold text-green-600">¥{balance.available_balance.toFixed(2)}</p>
                                    </div>
                                </div>
                                <div className="mt-4 text-sm text-muted-foreground">
                                    <p>最低提现金额：¥{balance.min_withdrawal_amount}</p>
                                    <p>提现手续费率：{(balance.withdrawal_fee_rate * 100).toFixed(0)}%</p>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* 提现表单 */}
                    <Card>
                        <CardHeader>
                            <CardTitle>申请提现</CardTitle>
                            <CardDescription>填写提现信息并提交申请</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="amount">提现金额</Label>
                                <Input
                                    id="amount"
                                    type="number"
                                    placeholder="请输入提现金额"
                                    value={withdrawalAmount}
                                    onChange={(e) => setWithdrawalAmount(e.target.value)}
                                />
                                {balance && withdrawalAmount && (
                                    <p className="text-sm text-muted-foreground">
                                        手续费：¥{(parseFloat(withdrawalAmount) * balance.withdrawal_fee_rate).toFixed(2)}，
                                        实际到账：¥{(parseFloat(withdrawalAmount) * (1 - balance.withdrawal_fee_rate)).toFixed(2)}
                                    </p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="payment-method">支付方式</Label>
                                <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择支付方式"/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="bank_transfer">银行转账</SelectItem>
                                        <SelectItem value="wechat">微信</SelectItem>
                                        <SelectItem value="alipay">支付宝</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {paymentMethod === 'bank_transfer' && (
                                <div className="space-y-4 border rounded-lg p-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="bank_name">银行名称</Label>
                                        <Input
                                            id="bank_name"
                                            placeholder="例如：中国工商银行"
                                            value={accountInfo.bank_name}
                                            onChange={(e) => setAccountInfo({
                                                ...accountInfo,
                                                bank_name: e.target.value
                                            })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="account_number">银行卡号</Label>
                                        <Input
                                            id="account_number"
                                            placeholder="请输入银行卡号"
                                            value={accountInfo.account_number}
                                            onChange={(e) => setAccountInfo({
                                                ...accountInfo,
                                                account_number: e.target.value
                                            })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="account_holder">持卡人姓名</Label>
                                        <Input
                                            id="account_holder"
                                            placeholder="请输入持卡人姓名"
                                            value={accountInfo.account_holder}
                                            onChange={(e) => setAccountInfo({
                                                ...accountInfo,
                                                account_holder: e.target.value
                                            })}
                                        />
                                    </div>
                                </div>
                            )}

                            {(paymentMethod === 'wechat' || paymentMethod === 'alipay') && (
                                <div className="space-y-2">
                                    <Label
                                        htmlFor="account_id">{paymentMethod === 'wechat' ? '微信号' : '支付宝账号'}</Label>
                                    <Input
                                        id="account_id"
                                        placeholder={`请输入${paymentMethod === 'wechat' ? '微信号' : '支付宝账号'}`}
                                        value={accountInfo.account_number || ''}
                                        onChange={(e) => setAccountInfo({
                                            ...accountInfo,
                                            account_number: e.target.value
                                        })}
                                    />
                                </div>
                            )}

                            <Button onClick={handleWithdrawal} disabled={loading} className="w-full">
                                {loading ? '提交中...' : '提交提现申请'}
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 提现记录 */}
                <TabsContent value="history">
                    <Card>
                        <CardHeader>
                            <CardTitle>提现记录</CardTitle>
                            <CardDescription>查看您的历史提现申请</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {withdrawals.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    暂无提现记录
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {withdrawals.map((wd) => (
                                        <div key={wd.withdrawal_id}
                                             className="border rounded-lg p-4 space-y-2">
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <p className="font-semibold">¥{wd.amount.toFixed(2)}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        手续费：¥{wd.fee.toFixed(2)}，实际到账：¥{wd.actual_amount.toFixed(2)}
                                                    </p>
                                                </div>
                                                {getStatusBadge(wd.status)}
                                            </div>
                                            <div className="flex justify-between text-sm text-muted-foreground">
                                                <span>{getPaymentMethodLabel(wd.payment_method)}</span>
                                                <span>{new Date(wd.created_at).toLocaleString('zh-CN')}</span>
                                            </div>
                                            {wd.admin_note && (
                                                <div
                                                    className="text-sm text-muted-foreground mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded">
                                                    备注：{wd.admin_note}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
