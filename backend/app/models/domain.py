from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Program(str, Enum):
    amex_mr = "amex_mr"
    chase_ur = "chase_ur"
    united = "united"
    delta = "delta"
    marriott = "marriott"
    hilton = "hilton"


class IngestionSource(str, Enum):
    browser_extension = "browser_extension"
    local_helper = "local_helper"
    manual_import = "manual_import"
    demo_seed = "demo_seed"


class IngestionStatus(str, Enum):
    success = "success"
    parse_error = "parse_error"
    sanity_failed = "sanity_failed"


class BookingType(str, Enum):
    cash = "cash"
    points = "points"
    hybrid = "hybrid"
    transfer = "transfer"
    offer_enhanced = "offer_enhanced"


class RankingMode(str, Enum):
    balanced = "balanced"
    lowest_out_of_pocket = "lowest_out_of_pocket"
    highest_cpp = "highest_cpp"
    total_value = "total_value"
    simplest = "simplest"


class ReservationCategory(str, Enum):
    car_rental = "car_rental"
    restaurant = "restaurant"


class ReservationStatus(str, Enum):
    planned = "planned"
    queued = "queued"
    pending_review = "pending_review"
    approved = "approved"
    dry_run_completed = "dry_run_completed"
    submitted = "submitted"
    confirmed = "confirmed"
    failed = "failed"
    cancelled = "cancelled"


class ReservationRiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LoyaltyAccount(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    program: Program
    display_name: str
    points_balance: int = Field(ge=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Offer(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    program: Optional[Program] = None
    merchant: str
    description: str
    value_usd: float = Field(ge=0)
    min_spend_usd: float = Field(default=0, ge=0)
    expires_on: Optional[date] = None


class TransferBonus(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    from_program: Program
    to_program: Program
    bonus_pct: float = Field(ge=0)
    valid_through: Optional[date] = None


class TripIntent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    raw_intent: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    budget_usd: float = Field(default=2000, gt=0)
    preferred_programs: List[Program] = Field(default_factory=list)
    ranking_mode: RankingMode = RankingMode.balanced


class TravelSearchRequest(BaseModel):
    user_id: UUID
    raw_intent: str
    origin: Optional[str] = None
    destination: str
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    adults: int = Field(default=1, ge=1, le=9)
    rooms: int = Field(default=1, ge=1, le=4)
    budget_usd: float = Field(default=2000, gt=0)
    direct_only: bool = False
    latest_arrival_time: Optional[time] = None
    hotel_min_stars: Optional[int] = Field(default=None, ge=1, le=5)
    hotel_max_travel_minutes: Optional[int] = Field(default=None, ge=1, le=240)
    preferred_programs: List[Program] = Field(default_factory=list)
    ranking_mode: RankingMode = RankingMode.balanced
    max_results: int = Field(default=8, ge=1, le=20)


class ReservationIntent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    category: ReservationCategory = ReservationCategory.car_rental
    raw_intent: str
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    pickup_date: Optional[date] = None
    pickup_time: Optional[time] = None
    dropoff_date: Optional[date] = None
    dropoff_time: Optional[time] = None
    vehicle_class: Optional[str] = None
    max_total_usd: Optional[float] = Field(default=None, gt=0)
    driver_age: Optional[int] = Field(default=None, ge=18, le=99)
    loyalty_programs: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class ReservationOption(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: ReservationCategory = ReservationCategory.car_rental
    provider: str
    merchant: str
    label: str
    total_price_usd: float = Field(ge=0)
    currency: str = "USD"
    booking_url: Optional[str] = None
    provider_reference: Optional[str] = None
    source_environment: Literal["production", "sandbox", "mock", "unknown"] = "mock"
    provider_confidence: float = Field(default=0.55, ge=0, le=1)
    pay_later: bool = True
    free_cancellation: bool = True
    cancellation_summary: Optional[str] = None
    requires_payment_now: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class ReservationPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    intent: ReservationIntent
    options: List[ReservationOption] = Field(default_factory=list)
    recommended_option_id: Optional[UUID] = None
    status: ReservationStatus = ReservationStatus.planned
    risk_level: ReservationRiskLevel = ReservationRiskLevel.low
    guardrail_results: List[Dict[str, Any]] = Field(default_factory=list)
    required_user_inputs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReservationQueueItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    plan: ReservationPlan
    selected_option_id: UUID
    status: ReservationStatus = ReservationStatus.pending_review
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    book_after: datetime
    approval_required: bool = True
    max_charge_usd: Optional[float] = Field(default=None, gt=0)


class UserApproval(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    queue_item_id: UUID
    approved_option_id: UUID
    max_charge_usd: Optional[float] = Field(default=None, gt=0)
    approval_scope: str
    expires_at: Optional[datetime] = None
    approved_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    queue_item_id: UUID
    agent_type: str = "car_rental_reservation"
    dry_run: bool = True
    status: ReservationStatus
    steps: List[str] = Field(default_factory=list)
    result_message: str
    provider_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReservationRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    queue_item_id: UUID
    option: ReservationOption
    status: ReservationStatus
    confirmation_number: Optional[str] = None
    cancellation_link: Optional[str] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReservationPlanRequest(BaseModel):
    intent: ReservationIntent
    max_options: int = Field(default=8, ge=1, le=12)


class ReservationQueueRequest(BaseModel):
    plan: ReservationPlan
    selected_option_id: Optional[UUID] = None
    review_window_hours: int = Field(default=1, ge=0, le=168)
    max_charge_usd: Optional[float] = Field(default=None, gt=0)


class ReservationApprovalRequest(BaseModel):
    approved_option_id: UUID
    max_charge_usd: Optional[float] = Field(default=None, gt=0)
    approval_scope: str = "dry-run car rental reservation only"
    expires_at: Optional[datetime] = None


class ReservationStateResponse(BaseModel):
    user_id: UUID
    queue: List[ReservationQueueItem] = Field(default_factory=list)
    approvals: List[UserApproval] = Field(default_factory=list)
    agent_runs: List[AgentRun] = Field(default_factory=list)
    records: List[ReservationRecord] = Field(default_factory=list)


class BookingOption(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    label: str
    booking_type: BookingType
    merchant: str
    cash_price_usd: float = Field(ge=0)
    taxes_usd: float = Field(default=0, ge=0)
    fees_usd: float = Field(default=0, ge=0)
    copay_usd: float = Field(default=0, ge=0)
    points_program: Optional[Program] = None
    points_used: int = Field(default=0, ge=0)
    transfer_from_program: Optional[Program] = None
    transfer_bonus_pct: float = Field(default=0, ge=0)
    offer_value_usd: float = Field(default=0, ge=0)
    simplicity: int = Field(default=3, ge=1, le=5)
    source_provider: Optional[str] = None
    source_environment: Literal["production", "sandbox", "mock", "unknown"] = "unknown"
    provider_confidence: float = Field(default=0.7, ge=0, le=1)
    provider_reference: Optional[str] = None
    booking_url: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class TravelSearchResponse(BaseModel):
    provider: str
    live: bool
    booking_options: List[BookingOption]
    warnings: List[str] = Field(default_factory=list)
    provider_statuses: List["ProviderStatus"] = Field(default_factory=list)


class ProviderStatus(BaseModel):
    provider: str
    category: Literal["flight", "hotel"]
    status: Literal["live", "fallback", "failed", "disabled"]
    environment: Literal["production", "sandbox", "mock", "unknown"] = "unknown"
    confidence: float = Field(default=0.7, ge=0, le=1)
    latency_ms: int = Field(default=0, ge=0)
    result_count: int = Field(default=0, ge=0)
    warnings: List[str] = Field(default_factory=list)


ProviderReadinessCategory = Literal["flight", "hotel", "location"]


class ProviderReadiness(BaseModel):
    provider: str
    category: ProviderReadinessCategory
    configured: bool
    environment: Literal["production", "sandbox", "mock", "unknown"]
    v1_role: str
    next_step: str


class AggregatedTravelSearchResponse(BaseModel):
    booking_options: List[BookingOption]
    provider_statuses: List[ProviderStatus] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    option: BookingOption
    rank: int
    cents_per_point: Optional[float]
    out_of_pocket_usd: float
    cash_avoided_usd: float
    effective_savings_usd: float
    total_economic_value_usd: float
    score: float
    reasons: List[str]


class OptimizationRequest(BaseModel):
    intent: TripIntent
    accounts: List[LoyaltyAccount] = Field(default_factory=list)
    offers: List[Offer] = Field(default_factory=list)
    transfer_bonuses: List[TransferBonus] = Field(default_factory=list)
    booking_options: Optional[List[BookingOption]] = None


class TravelOptimizationRequest(BaseModel):
    search: TravelSearchRequest
    accounts: List[LoyaltyAccount] = Field(default_factory=list)
    offers: List[Offer] = Field(default_factory=list)
    transfer_bonuses: List[TransferBonus] = Field(default_factory=list)


class TripDiscoveryRequest(BaseModel):
    search: TravelSearchRequest
    accounts: List[LoyaltyAccount] = Field(default_factory=list)
    offers: List[Offer] = Field(default_factory=list)
    transfer_bonuses: List[TransferBonus] = Field(default_factory=list)
    max_destinations: int = Field(default=5, ge=1, le=12)
    max_provider_calls: int = Field(default=24, ge=2, le=80)
    max_flight_minutes: Optional[int] = Field(default=None, ge=30, le=1440)
    max_drive_minutes: Optional[int] = Field(default=None, ge=30, le=720)
    max_nightly_rate_usd: Optional[float] = Field(default=None, gt=0)
    include_near_misses: bool = True


class OptimizationResponse(BaseModel):
    intent: TripIntent
    recommendations: List[Recommendation]
    generated_booking_options: List[BookingOption]
    provider_statuses: List[ProviderStatus] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ManualIngestionRequest(BaseModel):
    user_id: UUID
    source: IngestionSource = IngestionSource.manual_import
    accounts: List[LoyaltyAccount] = Field(default_factory=list)
    offers: List[Offer] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BalanceCorrectionRequest(BaseModel):
    points_balance: int = Field(ge=0)
    display_name: Optional[str] = None


class IngestionRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    source: IngestionSource
    status: IngestionStatus
    account_count: int
    offer_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class ManualIngestionResponse(BaseModel):
    run: IngestionRun
    accounts: List[LoyaltyAccount]
    offers: List[Offer]


class IngestionStateResponse(BaseModel):
    user_id: UUID
    accounts: List[LoyaltyAccount] = Field(default_factory=list)
    offers: List[Offer] = Field(default_factory=list)
    last_run: Optional[IngestionRun] = None


RecommendationSortKey = Literal[
    "lowest_out_of_pocket",
    "highest_cpp",
    "total_value",
    "simplest",
]
