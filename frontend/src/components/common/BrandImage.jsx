import React, { useState } from 'react';

export const BrandImage = ({ src, alt, className = '', loading = 'lazy' }) => {
  const [failed, setFailed] = useState(false);
  return <img
    className={className}
    src={failed ? '/images/cover-fallback.svg' : src}
    alt={alt}
    loading={loading}
    onError={() => setFailed(true)}
  />;
};
