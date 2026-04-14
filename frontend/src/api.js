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
  cart: () => request("/api/cart"),
  addToCart: (productId, quantity = 1) =>
    request("/api/cart", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    }),
  updateCart: (itemId, quantity) =>
    request(`/api/cart/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    }),
  removeCart: (itemId) => request(`/api/cart/${itemId}`, { method: "DELETE" }),
  placeOrder: (payload) =>
    request("/api/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  orders: () => request("/api/orders"),
  sellerDashboard: (sellerId) => request(`/api/seller/${sellerId}/dashboard`),
};
