/**
 * 购物车页�? */
'use client';

import {useEffect, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {useRouter} from 'next/navigation';

interface CartItem {
    id: number;
    product_id: number;
    quantity: number;
    product?: {
        id: number;
        name: string;
        slug: string;
        price: number;
        images?: Array<{ url: string }>;
        stock: number;
    };
}

interface CartResponse {
    success: boolean;
    data: {
        items: CartItem[];
        total: number;
        count: number;
    };
}

export default function CartPage() {
    const router = useRouter();
    const [cart, setCart] = useState<CartResponse['data'] | null>(null);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState<number | null>(null);

    useEffect(() => {
        fetchCart();
    }, []);

    const fetchCart = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/v2/ecommerce/cart');
            const data: CartResponse = await response.json();

            if (data.success) {
                setCart(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch cart:', error);
        } finally {
            setLoading(false);
        }
    };

    const updateQuantity = async (itemId: number, newQuantity: number) => {
        if (newQuantity < 1) return;

        setUpdating(itemId);
        try {
            const response = await fetch(`/api/v2/ecommerce/cart/items/${itemId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({quantity: newQuantity}),
            });

            const data = await response.json();

            if (data.success) {
                fetchCart();
            }
        } catch (error) {
            console.error('Failed to update quantity:', error);
        } finally {
            setUpdating(null);
        }
    };

    const removeItem = async (itemId: number) => {
        if (!confirm('确定要删除这个商品吗�?)) return;

        try {
            const response = await fetch(`/api/v2/ecommerce/cart/items/${itemId}`, {
                method: 'DELETE',
            });

            const data = await response.json();

            if (data.success) {
                fetchCart();
            }
        } catch (error) {
            console.error('Failed to remove item:', error);
        }
    };

    const clearCart = async () => {
        if (!confirm('确定要清空购物车吗？')) return;

        try {
            const response = await fetch('/api/v2/ecommerce/cart/clear', {
                method: 'POST',
            });

            const data = await response.json();

            if (data.success) {
                fetchCart();
            }
        } catch (error) {
            console.error('Failed to clear cart:', error);
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
                    <div className="space-y-4">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="bg-gray-200 h-32 rounded-lg"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (!cart || cart.items.length === 0) {
        return (
            <div className="container mx-auto px-4 py-8 text-center">
                <h1 className="text-2xl font-bold mb-4">购物车是空的</h1>
                <p className="text-gray-500 mb-6">快去选购心仪的商品吧�?/p>
                <Link
                    href="/products"
                    className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
                >
                    去购�? </Link>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold">购物�?({cart.count})</h1>
                <button
                    onClick={clearCart}
                    className="text-red-600 hover:text-red-700"
                >
                    清空购物�?
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Cart Items */}
                <div className="lg:col-span-2 space-y-4">
                    {cart.items.map((item) => (
                        <CartItemCard
                            key={item.id}
                            item={item}
                            updating={updating === item.id}
                            onUpdateQuantity={updateQuantity}
                            onRemove={removeItem}
                        />
                    ))}
                </div>

                {/* Order Summary */}
                <div className="lg:col-span-1">
                    <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
                        <h2 className="text-xl font-semibold mb-4">订单摘要</h2>

                        <div className="space-y-2 mb-4">
                            <div className="flex justify-between">
                                <span className="text-gray-600">商品数量</span>
                                <span>{cart.count}</span>
                            </div>
                            <div className="flex justify-between text-lg font-semibold">
                                <span>总计</span>
                                <span className="text-red-600">¥{cart.total.toFixed(2)}</span>
                            </div>
                        </div>

                        <Link
                            href="/checkout"
                            className="block w-full bg-blue-600 text-white text-center py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
                        >
                            去结�? </Link>

                        <Link
                            href="/products"
                            className="block w-full mt-2 text-center text-blue-600 hover:underline py-2"
                        >
                            继续购物
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}

function CartItemCard({
                          item,
                          updating,
                          onUpdateQuantity,
                          onRemove,
                      }: {
    item: CartItem;
    updating: boolean;
    onUpdateQuantity: (itemId: number, quantity: number) => void;
    onRemove: (itemId: number) => void;
}) {
    const product = item.product;

    if (!product) return null;

    const imageUrl = product.images?.[0]?.url || '/placeholder-product.png';

    return (
        <div className="bg-white rounded-lg shadow-md p-4 flex gap-4">
            {/* Product Image */}
            <Link href={`/products/${product.slug}`} className="relative w-32 h-32 flex-shrink-0">
                <Image
                    src={imageUrl}
                    alt={product.name}
                    fill
                    className="object-cover rounded-lg"
                />
            </Link>

            {/* Product Info */}
            <div className="flex-1">
                <Link href={`/products/${product.slug}`}>
                    <h3 className="font-semibold text-lg hover:text-blue-600 transition-colors">
                        {product.name}
                    </h3>
                </Link>

                <p className="text-red-600 font-bold mt-2">¥{product.price.toFixed(2)}</p>

                {/* Quantity Controls */}
                <div className="flex items-center gap-2 mt-4">
                    <button
                        onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
                        disabled={updating || item.quantity <= 1}
                        className="w-8 h-8 border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                        -
                    </button>

                    <span className="w-12 text-center">{item.quantity}</span>

                    <button
                        onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                        disabled={updating || item.quantity >= product.stock}
                        className="w-8 h-8 border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                        +
                    </button>
                </div>
            </div>

            {/* Remove Button */}
            <button
                onClick={() => onRemove(item.id)}
                className="text-gray-400 hover:text-red-600 transition-colors self-start"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                    />
                </svg>
            </button>
        </div>
    );
}
