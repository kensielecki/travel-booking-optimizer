export type Program = "amex_mr" | "chase_ur" | "united" | "delta" | "marriott" | "hilton";

export type BookingType = "cash" | "points" | "hybrid" | "transfer" | "offer_enhanced";

export type RankingMode = "balanced" | "lowest_out_of_pocket" | "highest_cpp" | "total_value" | "simplest";

export type ProviderCategory = "flight" | "hotel";

export type ProviderStatusValue = "live" | "fallback" | "failed" | "disabled";

export type ProviderReadinessCategory = "flight" | "hotel" | "location";

export interface BookingOption {
  label: string;
  booking_type: BookingType;
  merchant: string;
  cash_price_usd: number;
  taxes_usd: number;
  fees_usd: number;
  copay_usd: number;
  points_program?: Program;
  points_used: number;
  transfer_from_program?: Program;
  transfer_bonus_pct: number;
  offer_value_usd: number;
  simplicity: number;
  source_provider?: string | null;
  source_environment: "production" | "sandbox" | "mock" | "unknown";
  provider_confidence: number;
  notes: string[];
}

export interface Recommendation {
  option: BookingOption;
  rank: number;
  cents_per_point: number | null;
  out_of_pocket_usd: number;
  cash_avoided_usd: number;
  effective_savings_usd: number;
  total_economic_value_usd: number;
  score: number;
  reasons: string[];
}

export interface ProviderStatus {
  provider: string;
  category: ProviderCategory;
  status: ProviderStatusValue;
  environment: "production" | "sandbox" | "mock" | "unknown";
  confidence: number;
  latency_ms: number;
  result_count: number;
  warnings: string[];
}

export interface ProviderReadiness {
  provider: string;
  category: ProviderReadinessCategory;
  configured: boolean;
  environment: "production" | "sandbox" | "mock" | "unknown";
  v1_role: string;
  next_step: string;
}

export interface OptimizationResponse {
  intent: {
    raw_intent: string;
    destination?: string;
    budget_usd: number;
  };
  recommendations: Recommendation[];
  provider_statuses: ProviderStatus[];
  warnings: string[];
  generated_at: string;
}

export interface LoyaltyAccount {
  id: string;
  user_id: string;
  program: Program;
  display_name: string;
  points_balance: number;
  updated_at: string;
}

export interface Offer {
  id: string;
  user_id: string;
  program?: Program | null;
  merchant: string;
  description: string;
  value_usd: number;
  min_spend_usd: number;
  expires_on?: string | null;
}

export interface IngestionState {
  user_id: string;
  accounts: LoyaltyAccount[];
  offers: Offer[];
  last_run?: {
    id: string;
    source: string;
    status: string;
    account_count: number;
    offer_count: number;
    metadata?: {
      extraction_confidence?: number;
      detected_program?: Program | null;
      page_url_host?: string;
      warnings?: string[];
    };
    ingested_at: string;
  } | null;
}
