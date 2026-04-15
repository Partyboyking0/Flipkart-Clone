const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "flipkart_auth_token";
export const AUTH_EXPIRED_EVENT = "flipkart-auth-expired";
let authToken = "";

function readStoredToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

function writeStoredToken(token) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

function clearTokenState() {
  authToken = "";
  writeStoredToken("");
}

function notifyAuthExpired(message) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(AUTH_EXPIRED_EVENT, {
      detail: { message: message || "Session expired. Please login again." },
    }),
  );
}

async function request(path, options = {}) {
  const { auth = true, headers = {}, ...fetchOptions } = options;
  const hasAuthHeader = auth && Boolean(authToken);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(hasAuthHeader ? { Authorization: `Bearer ${authToken}` } : {}),
      ...headers,
    },
    ...fetchOptions,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg).join(", ")
      : payload.detail;
    if (response.status === 401 && hasAuthHeader) {
      clearTokenState();
      notifyAuthExpired(detail);
    }
    throw new Error(detail || "Something went wrong");
  }

  return response.json();
}

export const api = {
  hydrateToken: () => {
    authToken = readStoredToken();
    return authToken;
  },
  setToken: (token) => {
    authToken = token || "";
    writeStoredToken(authToken);
  },
  clearToken: () => {
    clearTokenState();
  },
  hasToken: () => Boolean(authToken),

  // Auth
  signup: (payload) =>
    request("/api/auth/signup", { method: "POST", body: JSON.stringify(payload), auth: false }),
  login: (payload) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify(payload), auth: false }),
  googleLogin: (payload) =>
    request("/api/auth/oauth/google", { method: "POST", body: JSON.stringify(payload), auth: false }),
  me: () => request("/api/auth/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  aiChat: (payload) =>
    request("/api/ai/chat", { method: "POST", body: JSON.stringify(payload) }),
  aiHistory: () => request("/api/ai/history"),
  clearAiHistory: () => request("/api/ai/history", { method: "DELETE" }),

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
  reorder: (orderNumber) => request(`/api/orders/${orderNumber}/reorder`, { method: "POST" }),

  // Account
  updateProfile: (payload) =>
    request("/api/account/profile", { method: "PATCH", body: JSON.stringify(payload) }),
  addresses: () => request("/api/account/addresses"),
  addAddress: (payload) =>
    request("/api/account/addresses", { method: "POST", body: JSON.stringify(payload) }),
  updateAddress: (addressId, payload) =>
    request(`/api/account/addresses/${addressId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteAddress: (addressId) => request(`/api/account/addresses/${addressId}`, { method: "DELETE" }),
  paymentMethods: () => request("/api/account/payment-methods"),
  addPaymentMethod: (payload) =>
    request("/api/account/payment-methods", { method: "POST", body: JSON.stringify(payload) }),
  deletePaymentMethod: (paymentId) => request(`/api/account/payment-methods/${paymentId}`, { method: "DELETE" }),
  recentlyViewed: () => request("/api/account/recently-viewed"),
  recommendations: () => request("/api/account/recommendations"),
  complaints: () => request("/api/complaints"),
  addComplaint: (payload) =>
    request("/api/complaints", { method: "POST", body: JSON.stringify(payload) }),

  // Seller
  sellerDashboard: (sellerId) => request(`/api/seller/${sellerId}/dashboard`),
  createSellerProduct: (payload) =>
    request("/api/seller/products", { method: "POST", body: JSON.stringify(payload) }),
  updateSellerProduct: (productId, payload) =>
    request(`/api/seller/products/${productId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteSellerProduct: (productId) => request(`/api/seller/products/${productId}`, { method: "DELETE" }),
  sellerReviews: () => request("/api/seller/reviews"),
  respondToReview: (reviewId, response) =>
    request(`/api/seller/reviews/${reviewId}/response`, { method: "PATCH", body: JSON.stringify({ response }) }),
  updateSellerOrderItemStatus: (orderId, itemId, status) =>
    request(`/api/seller/orders/${orderId}/items/${itemId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),

  // Razorpay
  razorpayCreateOrder: () => request("/api/razorpay/create-order", { method: "POST" }),
  razorpayVerify: (payload) =>
    request("/api/razorpay/verify", { method: "POST", body: JSON.stringify(payload) }),

  // Admin
  adminDashboard: () => request("/api/admin/dashboard"),
  adminUpdateUser: (userId, payload) =>
    request(`/api/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminDeleteUser: (userId) => request(`/api/admin/users/${userId}`, { method: "DELETE" }),
  adminModerateProduct: (productId, payload) =>
    request(`/api/admin/products/${productId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminDeleteProduct: (productId) => request(`/api/admin/products/${productId}`, { method: "DELETE" }),
  adminUpdateTransaction: (transactionId, payload) =>
    request(`/api/admin/transactions/${transactionId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminUpdateComplaint: (complaintId, payload) =>
    request(`/api/admin/complaints/${complaintId}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
