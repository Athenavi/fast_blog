/**
 * 结账页面
 */
'use client';

import {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';

interface CartItem {
    id: number;
    product_id: number;
    quantity: number;
    product?: {
        name: string;
        price: number;
    };
}

interface ShippingAddress {
    full_name: string;
    email: string;
    phone: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    state?: string;
    postal_code: string;
    country: string;
}

export default function CheckoutPage() {
    const router = useRouter();
    const [cartItems, setCartItems] = useState<CartItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const [shippingAddress, setShippingAddress] = useState<ShippingAddress>({
        full_name: '',
        email: '',
        phone: '',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: 'CN',
    });

    const [paymentMethod, setPaymentMethod] = useState('stripe');
    const [paymentMethods, setPaymentMethods] = useState<any[]>([]);

    useEffect(() => {
        fetchCart();
        fetchPaymentMethods();
    }, []);

    const fetchCart = async () => {
        try {
            const response = await fetch('/api/v2/ecommerce/cart');
            const data = await response.json();

            if (data.success) {
                setCartItems(data.data.items);
                setTotal(data.data.total);
            } else {
                router.push('/cart');
            }
        } catch (error) {
            console.error('Failed to fetch cart:', error);
            router.push('/cart');
        } finally {
            setLoading(false);
        }
    };

    const fetchPaymentMethods = async () => {
        try {
            const response = await fetch('/api/v2/payment/methods');
            const data = await response.json();

            if (data.success) {
                setPaymentMethods(data.data.methods);
            }
        } catch (error) {
            console.error('Failed to fetch payment methods:', error);
        }
    };

    const handleAddressChange = (field: keyof ShippingAddress, value: string) => {
        setShippingAddress(prev => ({...prev, [field]: value}));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // 验证表单
        if (!shippingAddress.full_name || !shippingAddress.email || !shippingAddress.phone ||
            !shippingAddress.address_line1 || !shippingAddress.city || !shippingAddress.postal_code) {
            alert('请填写所有必填字�?);
            return;
        }

        setSubmitting(true);
        try {
            // 创建订单
            const orderResponse = await fetch('/api/v2/ecommerce/orders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    shipping_address: shippingAddress,
                    payment_method: paymentMethod,
                }),
            });

            const orderData = await orderResponse.json();

            if (!orderData.success) {
                throw new Error(orderData.error || '订单创建失败');
            }

            const orderId = orderData.data.order_id;

            // 创建支付
            const paymentResponse = await fetch('/api/v2/payment/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: orderId,
                    payment_method: paymentMethod,
                }),
            });

            const paymentData = await paymentResponse.json();

            if (paymentData.success) {
                // 根据支付方式跳转
                if (paymentMethod === 'stripe' && paymentData.data.client_secret) {
                    // TODO: 集成 Stripe Elements
                    alert('Stripe 支付集成开发中，请使用其他支付方式');
                } else if (paymentMethod === 'paypal' && paymentData.data.approval_url) {
                    window.location.href = paymentData.data.approval_url;
                } else if (paymentMethod === 'alipay' && paymentData.data.pay_url) {
                    window.location.href = paymentData.data.pay_url;
                } else if (paymentMethod === 'wechat' && paymentData.data.code_url) {
                    // 显示二维�?                    alert(`微信支付二维�? ${paymentData.data.code_url}`);
                } else {
                    // 模拟支付成功
                    alert('订单创建成功！正在跳转到支付页面...');
                    router.push(`/orders/${orderId}`);
                }
            } else {
                throw new Error(paymentData.error || '支付创建失败');
            }
        } catch (error: any) {
            console.error('Checkout failed:', error);
            alert(error.message || '结账失败，请重试');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-4">
                            <div className="bg-gray-200 h-64 rounded-lg"></div>
                            <div className="bg-gray-200 h-64 rounded-lg"></div>
                        </div>
                        <div className="bg-gray-200 h-96 rounded-lg"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-8">结账</h1>

            <form onSubmit={handleSubmit}>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column - Forms */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Shipping Address */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h2 className="text-xl font-semibold mb-4">收货地址</h2>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        姓名 <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={shippingAddress.full_name}
                                        onChange={(e) => handleAddressChange('full_name', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        邮箱 <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="email"
                                        value={shippingAddress.email}
                                        onChange={(e) => handleAddressChange('email', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        电话 <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="tel"
                                        value={shippingAddress.phone}
                                        onChange={(e) => handleAddressChange('phone', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">国家</label>
                                    <select
                                        value={shippingAddress.country}
                                        onChange={(e) => handleAddressChange('country', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg"
                                    >
                                        <option value="CN">中国</option>
                                        <option value="US">美国</option>
                                        <option value="UK">英国</option>
                                    </select>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium mb-1">
                                        地址�? <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={shippingAddress.address_line1}
                                        onChange={(e) => handleAddressChange('address_line1', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>

                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium mb-1">地址�?（选填�?/label>
                                    <input
                                        type="text"
                                        value={shippingAddress.address_line2}
                                        onChange={(e) => handleAddressChange('address_line2', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        城市 <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={shippingAddress.city}
                                        onChange={(e) => handleAddressChange('city', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">省份/�?/label>
                                    <input
                                        type="text"
                                        value={shippingAddress.state}
                                        onChange={(e) => handleAddressChange('state', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        邮政编码 <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={shippingAddress.postal_code}
                                        onChange={(e) => handleAddressChange('postal_code', e.target.value)}
                                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Payment Method */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h2 className="text-xl font-semibold mb-4">支付方式</h2>

                            <div className="space-y-3">
                                {paymentMethods.map((method) => (
                                    <label
                                        key={method.id}
                                        className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                                            paymentMethod === method.id ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                                        }`}
                                    >
                                        <input
                                            type="radio"
                                            name="payment_method"
                                            value={method.id}
                                            checked={paymentMethod === method.id}
                                            onChange={(e) => setPaymentMethod(e.target.value)}
                                            className="w-4 h-4"
                                        />
                                        <div className="flex-1">
                                            <p className="font-semibold">{method.name}</p>
                                            <p className="text-sm text-gray-500">{method.description}</p>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Order Summary */}
                    <div className="lg:col-span-1">
                        <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
                            <h2 className="text-xl font-semibold mb-4">订单摘要</h2>

                            {/* Cart Items */}
                            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
                                {cartItems.map((item) => (
                                    <div key={item.id} className="flex justify-between text-sm">
                    <span className="flex-1">
                      {item.product?.name} x {item.quantity}
                    </span>
                                        <span className="font-semibold">
                      ¥{((item.product?.price || 0) * item.quantity).toFixed(2)}
                    </span>
                                    </div>
                                ))}
                            </div>

                            <div className="border-t pt-4 space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-gray-600">小计</span>
                                    <span>¥{total.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">运费</span>
                                    <span className="text-green-600">免费</span>
                                </div>
                                <div className="flex justify-between text-lg font-bold border-t pt-2">
                                    <span>总计</span>
                                    <span className="text-red-600">¥{total.toFixed(2)}</span>
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={submitting}
                                className="w-full mt-6 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {submitting ? '处理�?..' : '提交订单'}
                            </button>

                            <Link
                                href="/cart"
                                className="block mt-2 text-center text-blue-600 hover:underline"
                            >
                                返回购物�? </Link>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    );
}
