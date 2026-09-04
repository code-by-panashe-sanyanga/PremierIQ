"use client";

export default function IqLoader({ label = "FETCHING LEAGUE DATA" }: { label?: string }) {
  return (
    <div className="iq-loader" role="status" aria-live="polite">
      <span className="iq-loader-scan" aria-hidden="true" />
      <span className="iq-loader-label">{label}</span>
    </div>
  );
}
