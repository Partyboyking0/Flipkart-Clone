from datetime import datetime

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
    is_active: bool
    seller_status: str
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
    listing_status: str
    approval_note: str
    low_stock_threshold: int
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
    credential: str = Field(min_length=20)
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
    label: str = Field(default="Home", min_length=2, max_length=60)
    customer_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=10, max_length=20)
    address_line: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=5, max_length=12)


class AddressUpdateIn(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=60)
    customer_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    address_line: str | None = Field(default=None, min_length=5, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    pincode: str | None = Field(default=None, min_length=5, max_length=12)
    is_default: bool | None = None


class AddressOut(BaseModel):
    id: int
    user_id: int
    label: str
    customer_name: str
    phone: str
    address_line: str
    city: str
    state: str
    pincode: str
    is_default: bool
    model_config = {"from_attributes": True}


class AccountUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    address_line: str | None = Field(default=None, min_length=5, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    pincode: str | None = Field(default=None, min_length=5, max_length=12)
    store_name: str | None = Field(default=None, max_length=160)


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


class SavedPaymentMethodIn(BaseModel):
    provider: str = Field(pattern="^(UPI|CARD|COD|STRIPE|RAZORPAY|PAYPAL)$")
    label: str = Field(min_length=2, max_length=80)
    upi_id: str | None = Field(default=None, max_length=120)
    card_last4: str | None = Field(default=None, max_length=4)
    is_default: bool = False

    @field_validator("upi_id", "card_last4", mode="before")
    @classmethod
    def blank_saved_payment_to_none(cls, value):
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_saved_payment(self):
        if self.provider == "UPI" and not self.upi_id:
            raise ValueError("UPI ID is required for UPI payment")
        if self.provider == "CARD" and (not self.card_last4 or len(self.card_last4) != 4):
            raise ValueError("Last 4 card digits are required for card payment")
        return self


class SavedPaymentMethodOut(BaseModel):
    id: int
    user_id: int
    provider: str
    label: str
    upi_id: str
    card_last4: str
    is_default: bool
    model_config = {"from_attributes": True}


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
    status: str
    tracking_status: str
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
    refund_status: str
    created_at: datetime
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
    low_stock_count: int
    pending_products: int


class SellerTopProductOut(BaseModel):
    product_id: int
    title: str
    units_sold: int
    revenue: float


class SellerDashboardOut(BaseModel):
    seller: UserOut
    products: list[ProductOut]
    orders: list[OrderOut]
    reviews: list["ReviewOut"]
    stats: SellerStatsOut
    top_products: list[SellerTopProductOut]


# ── Admin schemas ─────────────────────────────────────────────────────────────
class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    total_products: int
    total_orders: int
    total_revenue: float
    paid_orders: int
    pending_orders: int
    pending_sellers: int
    pending_products: int
    refunded_transactions: int


class GrowthStatsOut(BaseModel):
    users_last_7_days: int
    orders_last_7_days: int
    revenue_last_7_days: float
    users_growth_percent: float
    orders_growth_percent: float
    revenue_growth_percent: float


class PaymentTransactionOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    provider: str
    amount: float
    status: str
    reference: str
    refund_status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ComplaintIn(BaseModel):
    order_id: int | None = None
    product_id: int | None = None
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=5, max_length=1000)


class ComplaintUpdateIn(BaseModel):
    status: str = Field(pattern="^(OPEN|IN_REVIEW|RESOLVED|REJECTED)$")
    resolution_note: str | None = Field(default=None, max_length=1000)


class ComplaintOut(BaseModel):
    id: int
    user_id: int
    order_id: int | None
    product_id: int | None
    subject: str
    message: str
    status: str
    resolution_note: str
    created_at: datetime
    user: UserOut
    model_config = {"from_attributes": True}


class FraudFlagOut(BaseModel):
    id: int
    order_id: int
    reason: str
    severity: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminDashboardOut(BaseModel):
    stats: AdminStatsOut
    growth: GrowthStatsOut
    users: list[UserOut]
    products: list[ProductOut]
    orders: list[OrderOut]
    transactions: list[PaymentTransactionOut]
    complaints: list[ComplaintOut]
    fraud_flags: list[FraudFlagOut]


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
    seller_response: str
    seller_responded_at: datetime | None
    user: UserOut
    model_config = {"from_attributes": True}


class ReviewResponseIn(BaseModel):
    response: str = Field(min_length=2, max_length=1000)


class ProductSpecIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=255)


class SellerProductIn(BaseModel):
    category_slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=4, max_length=255)
    brand: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    price: float = Field(gt=0)
    mrp: float = Field(gt=0)
    stock: int = Field(ge=0)
    assured: bool = True
    low_stock_threshold: int = Field(default=5, ge=0, le=50)
    images: list[str] = Field(default_factory=list, max_length=6)
    specs: list[ProductSpecIn] = Field(default_factory=list, max_length=12)


class SellerProductUpdateIn(BaseModel):
    category_slug: str | None = Field(default=None, min_length=2, max_length=120)
    title: str | None = Field(default=None, min_length=4, max_length=255)
    brand: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    price: float | None = Field(default=None, gt=0)
    mrp: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    assured: bool | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0, le=50)
    images: list[str] | None = Field(default=None, max_length=6)
    specs: list[ProductSpecIn] | None = Field(default=None, max_length=12)


class OrderStatusUpdateIn(BaseModel):
    status: str = Field(pattern="^(PLACED|PACKED|SHIPPED|DELIVERED)$")


class AdminUserUpdateIn(BaseModel):
    role: str | None = Field(default=None, pattern="^(buyer|seller|admin)$")
    is_active: bool | None = None
    seller_status: str | None = Field(default=None, pattern="^(PENDING|APPROVED|REJECTED|SUSPENDED)$")


class ProductModerationIn(BaseModel):
    listing_status: str = Field(pattern="^(PENDING|APPROVED|REJECTED)$")
    approval_note: str | None = Field(default=None, max_length=255)


class RefundUpdateIn(BaseModel):
    refund_status: str = Field(pattern="^(NONE|REQUESTED|REFUNDED)$")


class ProductListOut(BaseModel):
    items: list[ProductOut]


class AddressListOut(BaseModel):
    items: list[AddressOut]


class SavedPaymentMethodListOut(BaseModel):
    items: list[SavedPaymentMethodOut]


class ComplaintListOut(BaseModel):
    items: list[ComplaintOut]


SellerDashboardOut.model_rebuild()


class AIChatMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AIChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AIChatMessageIn] = Field(default_factory=list, max_length=12)


class AIChatOut(BaseModel):
    reply: str
    model: str


class AIChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    model_name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AIChatHistoryOut(BaseModel):
    items: list[AIChatMessageOut]
