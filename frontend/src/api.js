const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg).join(", ")
      : payload.detail;
    throw new Error(detail || "Something went wrong");
  }

  return response.json();
}

export const api = {
  // Auth
  signup: (payload) =>
    request("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  googleLogin: (payload) =>
    request("/api/auth/oauth/google", { method: "POST", body: JSON.stringify(payload) }),
  aiChat: (payload) =>
    request("/api/ai/chat", { method: "POST", body: JSON.stringify(payload) }),

  // Catalog
  categories: () => request("/api/categories"),
  users: () => request("/api/users"),
  user: (id) => request(`/api/users/${id}`),
  products: (params = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) search.set(key, value);
    });
    const query = search.toString();
    return request(`/api/products${query ? `?${query}` : ""}`);
  },
  product: (id) => request(`/api/products/${id}`),

  // Cart
  cart: () => request("/api/cart"),
  addToCart: (productId, quantity = 1) =>
    request("/api/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity }) }),
  updateCart: (itemId, quantity) =>
    request(`/api/cart/${itemId}`, { method: "PATCH", body: JSON.stringify({ quantity }) }),
  removeCart: (itemId) => request(`/api/cart/${itemId}`, { method: "DELETE" }),

  // Wishlist
  wishlist: () => request("/api/wishlist"),
  toggleWishlist: (productId) => request(`/api/wishlist/${productId}`, { method: "POST" }),

  // Reviews
  reviews: (productId) => request(`/api/products/${productId}/reviews`),
  addReview: (payload) =>
    request("/api/reviews", { method: "POST", body: JSON.stringify(payload) }),

  // Orders
  placeOrder: (payload) =>
    request("/api/orders", { method: "POST", body: JSON.stringify(payload) }),
  orders: () => request("/api/orders"),
  order: (orderNumber) => request(`/api/orders/${orderNumber}`),

  // Seller
  sellerDashboard: (sellerId) => request(`/api/seller/${sellerId}/dashboard`),

  // Razorpay
  razorpayCreateOrder: () => request("/api/razorpay/create-order", { method: "POST" }),
  razorpayVerify: (payload) =>
    request("/api/razorpay/verify", { method: "POST", body: JSON.stringify(payload) }),

  // Admin
  adminDashboard: () => request("/api/admin/dashboard"),
  adminDeleteUser: (userId) => request(`/api/admin/users/${userId}`, { method: "DELETE" }),
  adminDeleteProduct: (productId) => request(`/api/admin/products/${productId}`, { method: "DELETE" }),
};
