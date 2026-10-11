import React from 'react';
import { OpenVibeLogo } from './OpenVibeLogo';

const links = [
  { title: 'Trust & policies', items: [['Privacy policy', 'privacy-policy'], ['Terms & conditions', 'terms'], ['Cookie policy', 'cookies-policy'], ['Refund policy', 'refund-policy']] },
  { title: 'Your choices', items: [['Consent preferences', 'consent'], ['Privacy requests', 'data-rights'], ['Grievance & concerns', 'grievance']] },
  { title: 'Responsible AI', items: [['AI transparency', 'ai-transparency'], ['Accessibility', 'accessibility'], ['Copyright', 'copyright']] },
];

export const Footer = ({ setActivePage }) => (
  <footer className="footer">
    <div className="container">
      <div className="footer-grid">
        <div className="footer-brand-column">
          <OpenVibeLogo size={27} />
          <p>Connect. Share. Engage. Responsibly.<br />A social platform prototype with AI-assisted moderation and privacy controls.</p>
        </div>
        {links.map((group) => <section className="footer-column" key={group.title}>
          <h2>{group.title}</h2>
          <ul>{group.items.map(([label, page]) => <li key={page}><button type="button" onClick={() => setActivePage(page)}>{label}</button></li>)}</ul>
        </section>)}
      </div>
      <div className="footer-bottom"><span>© 2026 OpenVibe</span><span>Project demonstration · AI predictions can be inaccurate</span></div>
    </div>
  </footer>
);
