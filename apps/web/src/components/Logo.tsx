/**
 * The Neon Palms mark.
 *
 * Inline rather than an <img> so it inherits currentColor and can be sized
 * with Tailwind without a second network request.
 */
export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role="img"
      aria-label="Neon Palms Casino Resort"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="npFelt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#12563F" />
          <stop offset="100%" stopColor="#062218" />
        </linearGradient>
        <linearGradient id="npNeon" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FF2E88" />
          <stop offset="55%" stopColor="#F5C518" />
          <stop offset="100%" stopColor="#22D3EE" />
        </linearGradient>
        <filter id="npGlow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="1.6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect width="64" height="64" rx="14" fill="url(#npFelt)" />
      <rect
        x="1.5"
        y="1.5"
        width="61"
        height="61"
        rx="12.5"
        fill="none"
        stroke="#F5C518"
        strokeOpacity="0.35"
      />

      <g
        filter="url(#npGlow)"
        fill="none"
        stroke="url(#npNeon)"
        strokeWidth="2.4"
        strokeLinecap="round"
      >
        <path d="M32 50 C31 42 30.5 36 32 29" />
        <path d="M32 29 C26 24 20 23.5 15 26" />
        <path d="M32 29 C38 24 44 23.5 49 26" />
        <path d="M32 29 C28 22 24 18.5 19 17" />
        <path d="M32 29 C36 22 40 18.5 45 17" />
        <path d="M32 29 C32 22 32 18 32 13" />
      </g>

      <circle cx="29.6" cy="30.4" r="1.5" fill="#F5C518" />
      <circle cx="34.4" cy="30.4" r="1.5" fill="#F5C518" />
      <path
        d="M20 51.5 H44"
        stroke="#F5C518"
        strokeOpacity="0.6"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}
