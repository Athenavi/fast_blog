'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Badge} from '@/components/ui/badge';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {CheckCircle, ExternalLink, Loader2, Wallet} from 'lucide-react';
import Link from 'next/link';

interface UserNFT {
    article_id: number;
    token_id: string;
    contract_address: string;
    metadata_uri: string;
    minted_at: string;
    network: string;
}

export default function NFTCollectionPage() {
    const [walletAddress, setWalletAddress] = useState('');
    const [nfts, setNfts] = useState<UserNFT[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // 连接钱包
    const connectWallet = async () => {
        if (typeof window !== 'undefined' && (window as any).ethereum) {
            try {
                const accounts = await (window as any).ethereum.request({
                    method: 'eth_requestAccounts'
                });
                setWalletAddress(accounts[0]);
                setSuccess('钱包连接成功');

                // 自动加载 NFT
                loadUserNFTs(accounts[0]);
            } catch (err: any) {
                setError(err.message || '连接钱包失失败');
            }
        } else {
            setError('请安装MetaMask 或其他Web3 钱包扩展');
        }
    };

    // 加载用户 NFT
    const loadUserNFTs = async (address: string) => {
        if (!address) {
            setError('请输入钱包地址');
            return;
        }

        try {
            setLoading(true);
            setError('');

            const response = await fetch(`/api/v2/nft/user/${address}`);
            if (response.ok) {
                const data = await response.json();
                setNfts(data.data.nfts);
            }
        } catch (err: any) {
            setError(err.message || '加载失失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
                    <Wallet className="w-8 h-8"/>
                    NFT 收藏
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                    查看和管理您拥有的文章NFT
                </p>
            </div>

            {/* 钱包连接 */}
            <Card className="mb-8">
                <CardHeader>
                    <CardTitle>连接钱包</CardTitle>
                    <CardDescription>
                        连接您的 Web3 钱包以查看NFT 收藏
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {error && (
                        <Alert variant="destructive" className="mb-4">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {success && (
                        <Alert className="mb-4 border-green-200 bg-green-50 dark:bg-green-950">
                            <CheckCircle className="h-4 w-4 text-green-600"/>
                            <AlertDescription className="text-green-800 dark:text-green-200">
                                {success}
                            </AlertDescription>
                        </Alert>
                    )}

                    <div className="flex gap-2">
                        <Input
                            placeholder="0x... 或点击连接钱包"
                            value={walletAddress}
                            onChange={(e) => setWalletAddress(e.target.value)}
                        />
                        <Button onClick={connectWallet}>
                            <Wallet className="w-4 h-4 mr-2"/>
                            连接钱包
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => loadUserNFTs(walletAddress)}
                            disabled={!walletAddress || loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin"/>
                                    加载中...
                                </>
                            ) : (
                                '加载 NFT？
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* NFT 列表 */}
            {nfts.length > 0 ? (
                <div>
                    <h2 className="text-xl font-semibold mb-4">
                        我的收藏 ({nfts.length})
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {nfts.map((nft) => (
                            <Card key={nft.token_id} className="hover:shadow-lg transition-shadow">
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle className="text-base">
                                            Article #{nft.article_id}
                                        </CardTitle>
                                        <Badge variant="outline">{nft.network}</Badge>
                                    </div>
                                    <CardDescription className="text-xs font-mono">
                                        Token ID: {nft.token_id}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="text-sm space-y-1">
                                        <div className="flex justify-between">
                                            <span className=" text-gray-600 dark:text-gray-400">铸造时间</span>
                                            <span className="text-xs">
                                                {new Date(nft.minted_at).toLocaleDateString('zh-CN')}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600 dark:text-gray-400">合约:</span>
                                            <span className="text-xs font-mono">
                                                {nft.contract_address.slice(0, 6)}...{nft.contract_address.slice(-4)}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1"
                                            asChild
                                        >
                                            <Link href={`/articles/${nft.article_id}`}>
                                                查看文章
                                            </Link>
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => {
                                                // 在实际实现中，这里应该跳转到 OpenSea
                                                window.open(`https://opensea.io/assets/${nft.network}/${nft.contract_address}/${nft.token_id}`, '_blank');
                                            }}
                                        >
                                            <ExternalLink className="w-4 h-4"/>
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            ) : walletAddress ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <Wallet className="w-16 h-16 mx-auto text-gray-300 mb-4"/>
                        <p className="text-gray-500">暂无 NFT 收藏</p>
                        <p className="text-sm text-gray-400 mt-2">
                            浏览文章并铸造NFT 来开始您的收藏 </p>
                        <Button className="mt-4" asChild>
                            <Link href="/articles">浏览文章</Link>
                        </Button>
                    </CardContent>
                </Card>
            ) : null}

            {/* 帮助信息 */}
            <Card className="mt-8 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <CardContent className="pt-6">
                    <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                        💡 什么是 NFT？ </h3>
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                        NFT（非同质化代币）是区块链上的唯一数字资产。将文章铸造为 NFT 可以： </p>
                    <ul className="list-disc list-inside text-sm text-blue-800 dark:text-blue-200 mt-2 space-y-1">
                        <li>证明文章的所有权和真实性</li>
                        <li>在区块链上永久保存创作记录</li>
                        <li>支持内容的交易和收藏</li>
                        <li>获得去中心化的内容认证</li>
                    </ul>
                </CardContent>
            </Card>
        </div>
    );
}
