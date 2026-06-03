interface BrandMarkProps {
  className?: string;
  title?: string;
}

export function BrandMark({ className = "h-11 w-11", title = "Travel Booking Optimizer" }: BrandMarkProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      role="img"
      aria-label={title}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="48" height="48" rx="10" fill="#111317" />
      <path
        d="M12 30.5C19.8 21 28.5 15.8 38 13.5"
        fill="none"
        stroke="#F7FAFC"
        strokeLinecap="round"
        strokeWidth="3"
      />
      <path
        d="M14.5 18.5 35.5 22 19.5 32.5l3-8.2-8-5.8Z"
        fill="none"
        stroke="#F7FAFC"
        strokeLinejoin="round"
        strokeWidth="3"
      />
      <circle cx="12" cy="30.5" r="3.8" fill="#00A88F" />
    </svg>
  );
}
