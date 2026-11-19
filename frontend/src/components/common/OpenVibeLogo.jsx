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
      <rect width="40" height="40" rx="13" fill="url(#openvibe-mark-gradient)" />
      <path d="M13.5 14.5 20 20m6.5-5.5L20 20m0 0v7" stroke="white" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="13" cy="13.5" r="3.1" fill="white" />
      <circle cx="27" cy="13.5" r="3.1" fill="white" />
      <circle cx="20" cy="28" r="3.1" fill="white" />
      <circle cx="20" cy="20" r="4.3" fill="#a8f0dd" stroke="white" strokeWidth="1.7" />
      <defs>
        <linearGradient id="openvibe-mark-gradient" x1="3" y1="3" x2="37" y2="38" gradientUnits="userSpaceOnUse">
          <stop stopColor="#536fe5" />
          <stop offset="1" stopColor="#129c91" />
        </linearGradient>
      </defs>
    </svg>
    {showText && <span className="openvibe-wordmark">Open<span>Vibe</span></span>}
  </span>
);
