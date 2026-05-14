'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from '@/components/ui/dialog';
import {CheckCircle, ExternalLink, Loader2, Wallet, XCircle} from 'lucide-react';

interface NFTInfo {
    token_id: string;
    contract_address: string;
    owner_address: string;
    metadata_uri: string;
    minted_at: string;
    transaction_hash: string;
    network: string;
    opensea_url?: string;
}

interface ArticleNFTManagerProps {
    articleId: number;
    articleTitle: string;
}

export default function ArticleNFTManager({articleId, articleTitle}: ArticleNFTManagerProps) {
    const [nftInfo, setNftInfo] = useState<NFTInfo | null>(null);
    const [loading, setLoading] = useState(false);
    const [walletAddress, setWalletAddress] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showMintDialog, setShowMintDialog] = useState(false);

    // 加载 NFT 信息
    useEffect(() => {
        loadNFTInfo();
    }, [articleId]);

    const loadNFTInfo = async () => {
        try {
            const response = await fetch(`/api/v2/nft/${articleId}`);
            if (response.ok) {
                const data = await response.json();
                setNftInfo(data.data);
            }
        } catch (err) {
            console.error('加载 NFT 信息失败:', err);
        }
    };

    // 铸'NFT
    const handleMint = async () => {
        if (!walletAddress) {
            setError('请输入钱包地址');
            return;
        }

        // 验证钱包地址格式
        if (!/^0x[a-fA-F0-9]{40}$/.test(walletAddress)) {
            setError('无效的钱包地址格式');
            return;
        }

        try {
            setLoading(true);
            setError('');
            setSuccess('');

            const response = await fetch('/api/v2/nft/mint', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    article_id: articleId,
                    owner_address: walletAddress
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                setSuccess('NFT 铸造成功！');
                setShowMintDialog(false);
                loadNFTInfo();
            } else {
                setError(data.detail || 'NFT 铸造失');
            }
        } catch (err: any) {
            setError(err.message || '网络错误');
        } finally {
            setLoading(false);
        }
    };

    // 连接钱包（模拟）
    const connectWallet = async () => {
        // 在实际实现中，这里应该使'web3.js 'ethers.js 连接真实钱包
        // 这里仅作为演'
        if (typeof window !== 'undefined' && (window as any).ethereum) {
            try {
                const accounts = await (window as any).ethereum.request({
                    method: 'eth_requestAccounts'
                });
                setWalletAddress(accounts[0]);
                setSuccess('钱包连接成功');
            } catch (err: any) {
                setError(err.message || '连接钱包失败');
            }
        } else {
            // 如果没有安装 MetaMask，提示用'            setError('请安'MetaMask 或其'Web3 钱包扩展');
        }
    };

    if (nftInfo) {
        // 已铸'NFT
        return (
            <Card
                className="border-green-200 dark:border-green-800 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950 dark:to-emerald-950">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-green-600"/>
                            <CardTitle className="text-lg">NFT 已铸</CardTitle>
                        </div>
                        <Badge variant="default" className="bg-green-600">
                            {nftInfo.network}
                        </Badge>
                    </div>
                    <CardDescription>
                        这篇文章已经铸造为 NFT，拥有区块链上的所有权证明
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                            <Label className="text-xs text-gray-500">Token ID</Label>
                            <p className="font-mono text-xs break-all">{nftInfo.token_id}</p>
                        </div>
                        <div>
                            <Label className="text-xs text-gray-500">合约地址</Label>
                            <p className="font-mono text-xs break-all">{nftInfo.contract_address}</p>
                        </div>
                        <div>
                            <Label className="text-xs text-gray-500">所有</Label>
                            <p className="font-mono text-xs break-all">{nftInfo.owner_address}</p>
                        </div>
                        <div>
                            <Label className="text-xs text-gray-500">铸造时</Label>
                            <p className="text-xs">{new Date(nftInfo.minted_at).toLocaleString('zh-CN')}</p>
                        </div>
                    </div>

                    {nftInfo.opensea_url && (
                        <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => window.open(nftInfo.opensea_url, '_blank')}
                        >
                            <ExternalLink className="w-4 h-4 mr-2"/>
                            'OpenSea 上查' </Button>
                    )}
                </CardContent>
            </Card>
        );
    }

    // 未铸'NFT
    return (
        <>
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Wallet className="w-5 h-5"/>
                        铸'NFT
                    </CardTitle>
                    <CardDescription>
                        将文'"{articleTitle}" 铸造为 NFT，获得区块链上的所有权证明
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {error && (
                        <Alert variant="destructive">
                            <XCircle className="h-4 w-4"/>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {success && (
                        <Alert className="border-green-200 bg-green-50 dark:bg-green-950">
                            <CheckCircle className="h-4 w-4 text-green-600"/>
                            <AlertDescription className="text-green-800 dark:text-green-200">
                                {success}
                            </AlertDescription>
                        </Alert>
                    )}

                    <div className="space-y-2">
                        <Label htmlFor="wallet">钱包地址</Label>
                        <div className="flex gap-2">
                            <Input
                                id="wallet"
                                placeholder="0x..."
                                value={walletAddress}
                                onChange={(e) => setWalletAddress(e.target.value)}
                            />
                            <Button variant="outline" onClick={connectWallet}>
                                连接钱包
                            </Button>
                        </div>
                        <p className="text-xs text-gray-500">
                            支持 MetaMask、WalletConnect 等主流钱' </p>
                    </div>

                    <Dialog open={showMintDialog} onOpenChange={setShowMintDialog}>
                        <DialogTrigger asChild>
                            <Button className="w-full" disabled={!walletAddress}>
                                铸'NFT
                            </Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>确认铸'NFT</DialogTitle>
                                <DialogDescription>
                                    这将把文'"{articleTitle}" 铸造为 NFT
                                </DialogDescription>
                            </DialogHeader>

                            <div className="space-y-4 py-4">
                                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">文章 ID:</span>
                                        <span className="font-mono">{articleId}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">所有'</span>
                                        <span className="font-mono text-xs">{walletAddress}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">网络:</span>
                                        <span>Ethereum (模拟)</span>
                                    </div>
                                </div>

                                <Alert>
                                    <AlertDescription>
                                        ⚠️ 当前为演示模式，不会真正消'Gas 费用
                                    </AlertDescription>
                                </Alert>
                            </div>

                            <div className="flex gap-2">
                                <Button variant="outline" className="flex-1" onClick={() => setShowMintDialog(false)}>
                                    取消
                                </Button>
                                <Button
                                    className="flex-1"
                                    onClick={handleMint}
                                    disabled={loading}
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="w-4 h-4 mr-2 animate-spin"/>
                                            铸造中...
                                        </>
                                    ) : (
                                        '确认铸'
                                    )}
                                </Button>
                            </div>
                        </DialogContent>
                    </Dialog>
                </CardContent>
            </Card>
        </>
    );
}
