/**
 * 产品列表页面
 *
 * 显示所有可用产品，支持搜索、筛选和分页
 */
'use client';

import {useEffect, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';

interface Product {
    id: number;
    name: string;
    slug: string;
    description: string;
    price: number;
    original_price?: number;
    stock: number;
    sku?: string;
    images?: Array<{ url: string }>;
    category?: { name: string };
}

interface ProductsResponse {
    success: boolean;
    data: {
        products: Product[];
        total: number;
        page: number;
        per_page: number;
        pages: number;
    };
}

export default function ProductsPage() {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [search, setSearch] = useState('');
    const [category, setCategory] = useState('');
    const [sortBy, setSortBy] = useState('created_at');
    const [order, setOrder] = useState('desc');

    useEffect(() => {
        fetchProducts();
    }, [page, search, category, sortBy, order]);

    const fetchProducts = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: '12',
                ...(search && {search}),
                ...(category && {category_id: category}),
                sort_by: sortBy,
                order,
            });

            const response = await fetch(`/api/v2/ecommerce/products?${params}`);
            const data: ProductsResponse = await response.json();

            if (data.success) {
                setProducts(data.data.products);
                setTotalPages(data.data.pages);
            }
        } catch (error) {
            console.error('Failed to fetch products:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchProducts();
    };

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-4">产品列表</h1>

                {/* Search and Filters */}
                <form onSubmit={handleSearch} className="flex gap-4 mb-4">
                    <input
                        type="text"
                        placeholder="搜索产品..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                        type="submit"
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                        搜索
                    </button>
                </form>

                {/* Sort Options */}
                <div className="flex gap-4 items-center">
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        className="px-4 py-2 border rounded-lg"
                    >
                        <option value="created_at">最新上�?/option>
                        <option value="price">价格</option>
                        <option value="name">名称</option>
                    </select>

                    <button
                        onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')}
                        className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                    >
                        {order === 'asc' ? '�?升序' : '�?降序'}
                    </button>
                </div>
            </div>

            {/* Products Grid */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {[...Array(8)].map((_, i) => (
                        <div key={i} className="animate-pulse">
                            <div className="bg-gray-200 h-64 rounded-lg mb-4"></div>
                            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                        </div>
                    ))}
                </div>
            ) : products.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-gray-500 text-lg">暂无产品</p>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {products.map((product) => (
                            <ProductCard key={product.id} product={product}/>
                        ))}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="mt-8 flex justify-center gap-2">
                            <button
                                onClick={() => setPage(Math.max(1, page - 1))}
                                disabled={page === 1}
                                className="px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                            >
                                上一�?
                            </button>

                            <span className="px-4 py-2">
                �?{page} / {totalPages} �?              </span>

                            <button
                                onClick={() => setPage(Math.min(totalPages, page + 1))}
                                disabled={page === totalPages}
                                className="px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                            >
                                下一�?
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function ProductCard({product}: { product: Product }) {
    const imageUrl = product.images?.[0]?.url || '/placeholder-product.png';
    const hasDiscount = product.original_price && product.original_price > product.price;

    return (
        <Link href={`/products/${product.slug}`} className="block group">
            <div
                className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300">
                {/* Product Image */}
                <div className="relative h-64 bg-gray-100">
                    <Image
                        src={imageUrl}
                        alt={product.name}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-300"
                    />

                    {/* Stock Badge */}
                    {product.stock === 0 && (
                        <div className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded text-sm">
                            缺货
                        </div>
                    )}

                    {/* Discount Badge */}
                    {hasDiscount && (
                        <div className="absolute top-2 left-2 bg-green-500 text-white px-2 py-1 rounded text-sm">
                            -{Math.round(((product.original_price! - product.price) / product.original_price!) * 100)}%
                        </div>
                    )}
                </div>

                {/* Product Info */}
                <div className="p-4">
                    <h3 className="font-semibold text-lg mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
                        {product.name}
                    </h3>

                    {product.category && (
                        <p className="text-sm text-gray-500 mb-2">{product.category.name}</p>
                    )}

                    <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-red-600">
              ¥{product.price.toFixed(2)}
            </span>

                        {hasDiscount && (
                            <span className="text-sm text-gray-400 line-through">
                ¥{product.original_price!.toFixed(2)}
              </span>
                        )}
                    </div>

                    {product.stock > 0 && product.stock <= 10 && (
                        <p className="text-sm text-orange-500 mt-2">
                            仅剩 {product.stock} �? </p>
                    )}
                </div>
            </div>
        </Link>
    );
}
