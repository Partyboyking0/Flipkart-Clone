from pydantic import BaseModel, Field, field_validator, model_validator


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    model_config = {"from_attributes": True}


class ProductImageOut(BaseModel):
    id: int
    url: str
    alt: str
    model_config = {"from_attributes": True}


class ProductSpecOut(BaseModel):
    id: int
    name: str
    value: str
    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: str
    oauth_provider: str
    address_line: str
    city: str
    state: str
    pincode: str
    store_name: str
    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    title: str
    brand: str
    description: str
    price: float
    mrp: float
    rating: float
    reviews: int
    stock: int
    assured: bool
    seller_id: int
    category: CategoryOut
    images: list[ProductImageOut]
    specs: list[ProductSpecOut]
    model_config = {"from_attributes": True}


class AuthIn(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=6, max_length=80)


class SignupIn(AuthIn):
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=10, max_length=20)


class OAuthIn(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    name: str = Field(min_length=2, max_length=160)
    provider: str = Field(default="google", max_length=40)


class AuthOut(BaseModel):
    user: UserOut
    token: str


class CartAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=10)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=1, le=10)


class CartLineOut(BaseModel):
    id: int
    quantity: int
    product: ProductOut
    model_config = {"from_attributes": True}


class CartSummaryOut(BaseModel):
    mrp_total: float
    subtotal: float
    discount: float
    delivery_fee: float
    total: float


class CartOut(BaseModel):
    items: list[CartLineOut]
    summary: CartSummaryOut


class WishlistOut(BaseModel):
    items: list[ProductOut]


class AddressIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=10, max_length=20)
    address_line: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=5, max_length=12)


class PaymentIn(BaseModel):
    method: str = Field(pattern="^(UPI|CARD|COD|STRIPE|RAZORPAY|PAYPAL)$")
    payer_name: str = Field(min_length=2, max_length=160)
    upi_id: str | None = Field(default=None, max_length=120)
    card_last4: str | None = Field(default=None, max_length=4)
    payment_reference: str | None = Field(default=None, max_length=120)
    razorpay_order_id: str | None = Field(default=None, max_length=120)

    @field_validator("upi_id", "card_last4", "payment_reference", "razorpay_order_id", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_method_details(self):
        if self.method == "UPI" and not self.upi_id:
            raise ValueError("UPI ID is required for UPI payment")
        if self.method == "CARD" and (not self.card_last4 or len(self.card_last4) != 4):
            raise ValueError("Last 4 card digits are required for card payment")
        return self


class CheckoutIn(BaseModel):
    address: AddressIn
    payment: PaymentIn


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    title: str
    price: float
    quantity: int
    seller_id: int
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_number: str
    user_id: int
    customer_name: str
    phone: str
    address_line: str
    city: str
    state: str
    pincode: str
    total_amount: float
    payment_method: str
    payment_status: str
    payment_reference: str
    status: str
    tracking_status: str
    items: list[OrderItemOut]
    model_config = {"from_attributes": True}


# ── Razorpay schemas ──────────────────────────────────────────────────────────
class RazorpayOrderOut(BaseModel):
    razorpay_order_id: str
    amount: int          # in paise
    currency: str
    key_id: str


class RazorpayVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ── Seller schemas ────────────────────────────────────────────────────────────
class SellerStatsOut(BaseModel):
    product_count: int
    units_sold: int
    revenue: float
    order_count: int


class SellerDashboardOut(BaseModel):
    seller: UserOut
    products: list[ProductOut]
    orders: list[OrderOut]
    stats: SellerStatsOut


# ── Admin schemas ─────────────────────────────────────────────────────────────
class AdminStatsOut(BaseModel):
    total_users: int
    total_products: int
    total_orders: int
    total_revenue: float
    paid_orders: int
    pending_orders: int


class AdminDashboardOut(BaseModel):
    stats: AdminStatsOut
    users: list[UserOut]
    products: list[ProductOut]
    orders: list[OrderOut]


# ── Review schemas ────────────────────────────────────────────────────────────
class ReviewIn(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=800)


class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: str
    verified_purchase: bool
    user: UserOut
    model_config = {"from_attributes": True}


class AIChatMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AIChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AIChatMessageIn] = Field(default_factory=list, max_length=12)


class AIChatOut(BaseModel):
    reply: str
    model: str
