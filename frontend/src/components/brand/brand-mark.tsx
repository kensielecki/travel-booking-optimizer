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
        d="M13 30.6c6.3-9.9 15.2-15.7 25-17.9"
        fill="none"
        stroke="#F7FAFC"
        strokeLinecap="round"
        strokeWidth="3.2"
      />
      <path
        d="M15.6 16.7 35.4 22 19.1 34.4l2.6-10.3-6.1-7.4Z"
        fill="none"
        stroke="#F7FAFC"
        strokeLinejoin="round"
        strokeWidth="2.8"
      />
      <circle cx="13" cy="30.6" r="4.4" fill="#00A88F" />
      <circle cx="38" cy="12.7" r="3.2" fill="#FF6B35" />
      <path
        d="M28.4 29.6h7.8m-3.9-3.9v7.8"
        stroke="#C9A44C"
        strokeLinecap="round"
        strokeWidth="2.4"
      />
    </svg>
  );
}
