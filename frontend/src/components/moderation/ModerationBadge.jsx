import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldAlert, Clock, CircleHelp } from 'lucide-react';

const statusPresentation = {
  APPROVED: { label: 'Published', Icon: CheckCircle2, tone: 'status-approved', description: 'This content is visible in the approved feed.' },
  FLAGGED_FOR_REVIEW: { label: 'Under review', Icon: Clock, tone: 'status-review', description: 'This content is waiting for an administrator to review it.' },
  BLOCKED: { label: 'Not published', Icon: ShieldAlert, tone: 'status-blocked', description: 'This content is not available in the public feed.' },
};

const classificationTone = (label) => {
  if (label === 'Hate Speech') return 'badge-hate';
  if (label === 'Offensive') return 'badge-offensive';
  if (label === 'Normal') return 'badge-normal';
  return 'badge-neutral';
};

export const ModerationBadge = ({ prediction, status }) => {
  const label = prediction?.label || prediction?.predicted_class;
  const confidence = typeof prediction?.confidence === 'number' ? prediction.confidence : null;
  const confidenceLevel = prediction?.confidence_level;
  const statusInfo = statusPresentation[status];
  if (!label && !statusInfo) return null;
  const StatusIcon = statusInfo?.Icon || CircleHelp;

  return (
    <div className="moderation-badges" aria-label="Moderation result">
      {label && <span className={`badge ${classificationTone(label)}`} title="Automated classification returned by the moderation service">
        {label === 'Normal' ? <CheckCircle2 size={14} aria-hidden="true" /> : label === 'Hate Speech' ? <ShieldAlert size={14} aria-hidden="true" /> : <AlertTriangle size={14} aria-hidden="true" />}
        <span>{label}</span>
        {confidence !== null && <span className="badge-confidence">{Math.round(confidence * 100)}%</span>}
      </span>}
      {statusInfo && <span className={`status-pill ${statusInfo.tone}`} title={statusInfo.description}>
        <StatusIcon size={14} aria-hidden="true" /> {statusInfo.label}
      </span>}
      {confidenceLevel === 'LOW' && <span className="status-pill status-review" title="Low AI confidence may require careful human review">
        <AlertTriangle size={14} aria-hidden="true" /> Low confidence
      </span>}
    </div>
  );
};
