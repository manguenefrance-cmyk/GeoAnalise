import Image from "next/image";
export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a className="brand" href="/" aria-label="ARCAMBE GeoAnalytics">
      <span className="brand-icon">
        <Image
          src="/brand/arcambe-symbol.png"
          alt=""
          width={48}
          height={48}
          priority
        />
      </span>
      {!compact && (
        <span>
          <strong>ARCAMBE</strong>
          <small>GEOANALYTICS</small>
        </span>
      )}
    </a>
  );
}
