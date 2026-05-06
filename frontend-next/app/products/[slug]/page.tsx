/**
 * 产品详情页面
 */
'use client';

import {useEffect, useState} from 'react';
import {useParams, useRouter} from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';

interface Product {
    id: number;
    name: string;
    slug: string;
    description: string;
    price: number;
    original_price?: number;
    stock: number;
    sku?: string;
    images?: Array<{ url: string; alt?: string }>;
    category?: { id: number; name: string };
    created_at?: string;
}

export default function ProductDetailPage() {
    const params = useParams();
    const router = useRouter();
    const slug = params.slug as string;

    const [product, setProduct] = useState<Product | null>(null);
    const [loading, setLoading] = useState(true);
    const [quantity, setQuantity] = useState(1);
    const [selectedImage, setSelectedImage] = useState(0);
    const [addingToCart, setAddingToCart] = useState(false);

    useEffect(() => {
        if (slug) {
            fetchProduct();
        }
    }, [slug]);

    const fetchProduct = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/v1/ecommerce/products/slug/${slug}`);
            const data = await response.json();

            if (data.success) {
                setProduct(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch product:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddToCart = async () => {
        if (!product) return;

        setAddingToCart(true);
        try {
            const response = await fetch('/api/v1/ecommerce/cart/items', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_id: product.id,
                    quantity: quantity,
                }),
            });

            const data = await response.json();

            if (data.success) {
                alert('已添加到购物车！');
                router.push('/cart');
            } else {
                alert(data.error || '添加失败');
            }
        } catch (error) {
            console.error('Failed to add to cart:', error);
            alert('添加失败，请重试');
        } finally {
            setAddingToCart(false);
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="animate-pulse">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="bg-gray-200 h-96 rounded-lg"></div>
                        <div>
                            <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
                            <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (!product) {
        return (
            <div className="container mx-auto px-4 py-8 text-center">
                <h1 className="text-2xl font-bold mb-4">产品未找到</h1>
                <Link href="/products" className="text-blue-600 hover:underline">
                    返回产品列表
                </Link>
            </div>
        );
    }

    const hasDiscount = product.original_price && product.original_price > product.price;
    const mainImage = product.images?.[selectedImage]?.url || '/placeholder-product.png';

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Breadcrumb */}
            <nav className="mb-6 text-sm">
                <Link href="/" className="text-gray-600 hover:text-blue-600">首页</Link>
                <span className="mx-2 text-gray-400">/</span>
                <Link href="/products" className="text-gray-600 hover:text-blue-600">产品</Link>
                <span className="mx-2 text-gray-400">/</span>
                <span className="text-gray-900">{product.name}</span>
            </nav>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Product Images */}
                <div>
                    <div className="relative h-96 bg-gray-100 rounded-lg overflow-hidden mb-4">
                        <Image
                            src={mainImage}
                            alt={product.name}
                            fill
                            className="object-cover"
                        />
                    </div>

                    {/* Thumbnail Gallery */}
                    {product.images && product.images.length > 1 && (
                        <div className="flex gap-2 overflow-x-auto">
                            {product.images.map((image, index) => (
                                <button
                                    key={index}
                                    onClick={() => setSelectedImage(index)}
                                    className={`relative w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden border-2 ${
                                        selectedImage === index ? 'border-blue-500' : 'border-transparent'
                                    }`}
                                >
                                    <Image
                                        src={image.url}
                                        alt={image.alt || product.name}
                                        fill
                                        className="object-cover"
                                    />
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Product Info */}
                <div>
                    <h1 className="text-3xl font-bold mb-4">{product.name}</h1>

                    {product.category && (
                        <Link
                            href={`/products?category=${product.category.id}`}
                            className="inline-block text-sm text-blue-600 hover:underline mb-4"
                        >
                            {product.category.name}
                        </Link>
                    )}

                    {/* Price */}
                    <div className="mb-6">
                        <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-red-600">
                ¥{product.price.toFixed(2)}
              </span>
                            {hasDiscount && (
                                <span className="text-lg text-gray-400 line-through">
                  ¥{product.original_price!.toFixed(2)}
                </span>
                            )}
                        </div>
                        {hasDiscount && (
                            <p className="text-sm text-green-600 mt-1">
                                节省 ¥{(product.original_price! - product.price).toFixed(2)}
                            </p>
                        )}
                    </div>

                    {/* Stock Status */}
                    <div className="mb-6">
                        {product.stock === 0 ? (
                            <p className="text-red-500 font-semibold">缺货</p>
                        ) : product.stock <= 10 ? (
                            <p className="text-orange-500">仅剩 {product.stock} 件库存</p>
                        ) : (
                            <p className="text-green-600">有货</p>
                        )}
                    </div>

                    {/* Description */}
                    {product.description && (
                        <div className="mb-6">
                            <h2 className="text-lg font-semibold mb-2">产品描述</h2>
                            <p className="text-gray-700 whitespace-pre-line">{product.description}</p>
                        </div>
                    )}

                    {/* SKU */}
                    {product.sku && (
                        <p className="text-sm text-gray-500 mb-6">SKU: {product.sku}</p>
                    )}

                    {/* Quantity Selector */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">数量</label>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                                className="w-10 h-10 border rounded-lg hover:bg-gray-100"
                                disabled={product.stock === 0}
                            >
                                -
                            </button>
                            <input
                                type="number"
                                value={quantity}
                                onChange={(e) => setQuantity(Math.max(1, Math.min(product.stock, parseInt(e.target.value) || 1)))}
                                className="w-20 h-10 text-center border rounded-lg"
                                min="1"
                                max={product.stock}
                                disabled={product.stock === 0}
                            />
                            <button
                                onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}
                                className="w-10 h-10 border rounded-lg hover:bg-gray-100"
                                disabled={product.stock === 0 || quantity >= product.stock}
                            >
                                +
                            </button>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-4">
                        <button
                            onClick={handleAddToCart}
                            disabled={product.stock === 0 || addingToCart}
                            className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {addingToCart ? '添加中...' : '加入购物车'}
                        </button>

                        {product.stock > 0 && (
                            <button
                                onClick={handleAddToCart}
                                className="flex-1 bg-red-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-700 transition"
                            >
                                立即购买
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Related Products Section (TODO) */}
            <div className="mt-12">
                <h2 className="text-2xl font-bold mb-6">相关产品</h2>
                <p className="text-gray-500">功能开发中...</p>
            </div>
        </div>
    );
}
