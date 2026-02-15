import { Doll } from '../api/dolls';
import { getMediaUrl } from '../api/client';

interface DollCardProps {
  doll: Doll;
  onClick: () => void;
}

export function DollCard({ doll, onClick }: DollCardProps) {
  const photoUrl = doll.primary_photo_url ? getMediaUrl(doll.primary_photo_url) : null;

  return (
    <div className="doll-card" onClick={onClick}>
      <div className="doll-card-image">
        {photoUrl ? (
          <img src={photoUrl} alt={doll.name} />
        ) : (
          <div className="doll-card-placeholder">
            <span>📷</span>
          </div>
        )}
      </div>
      <div className="doll-card-name">{doll.name}</div>
    </div>
  );
}

