import { TripOptimizer } from "@/components/trip-optimizer";

const DEMO_USER_ID = "11111111-1111-4111-8111-111111111111";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  return <TripOptimizer apiUrl={API_URL} userId={DEMO_USER_ID} />;
}
