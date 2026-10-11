import React, { useState } from 'react';

export const Avatar = ({ name = 'OpenVibe member', src, size = 'md', className = '' }) => {
  const [failed, setFailed] = useState(false);
  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'OV';

  if (src && !failed) {
    return <img className={`avatar avatar-${size} ${className}`} src={src} alt={`${name}, profile`} loading="lazy" onError={() => setFailed(true)} />;
  }

  return <span className={`avatar avatar-${size} avatar-initial ${className}`} aria-label={`${name}, profile`}>{initials}</span>;
};
