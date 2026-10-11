import React from 'react';

export const OpenVibeLogo = ({ size = 30, showText = true, className = '' }) => (
  <span className={`openvibe-logo-container ${className}`}>
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="40" height="40" rx="12" fill="url(#openvibe-mark-gradient)" />
      <path d="M10 13.5C10 11.567 11.567 10 13.5 10H26.5C28.433 10 30 11.567 30 13.5V22.5C30 24.433 28.433 26 26.5 26H20L14.5 30V26H13.5C11.567 26 10 24.433 10 22.5V13.5Z" stroke="white" strokeWidth="2.2" strokeLinejoin="round" />
      <circle cx="16" cy="18" r="1.5" fill="white" />
      <circle cx="20" cy="18" r="1.5" fill="white" />
      <circle cx="24" cy="18" r="1.5" fill="white" />
      <defs>
        <linearGradient id="openvibe-mark-gradient" x1="4" y1="4" x2="38" y2="38" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2769E8" />
          <stop offset="1" stopColor="#15A7A0" />
        </linearGradient>
      </defs>
    </svg>
    {showText && <span className="openvibe-wordmark">Open<span>Vibe</span></span>}
  </span>
);
