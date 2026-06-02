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
