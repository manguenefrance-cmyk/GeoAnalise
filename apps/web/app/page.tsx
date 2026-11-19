"use client";
import Link from "next/link";
import { Satellite, ScanLine, FileStack, Globe2 } from "lucide-react";
import Brand from "@/components/Brand";
import { useApp } from "@/lib/context";
export default function Home() {
  const { t, locale, setLocale } = useApp();
  return (
    <main className="landing">
      <nav className="landing-nav">
        <Brand />
        <div>
          <button
            className="text-button"
            onClick={() => setLocale(locale === "en" ? "pt" : "en")}
          >
            <Globe2 size={16} />
            {locale === "en" ? "PT" : "EN"}
          </button>
          <Link href="/auth/login" className="button secondary">
            {t.login}
          </Link>
        </div>
      </nav>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="status-dot" /> EARTH OBSERVATION / ARCAMBE
          </div>
          <h1>{t.tagline}</h1>
          <p>{t.intro}</p>
          <Link className="button primary large" href="/app/dashboard">
            {t.start}
          </Link>
          <div className="hero-foot">
            SENTINEL-2 L2A <span>•</span> 10–20 m <span>•</span> EN / PT
          </div>
        </div>
        <div className="hero-map" aria-label={t.mapAttribution}>
          <div className="contour c1" />
          <div className="contour c2" />
          <div className="contour c3" />
          <div className="contour c4" />
          <svg
            viewBox="0 0 500 500"
            role="img"
            aria-label={
              locale === "pt"
                ? "Ilustração cartográfica; não é um resultado de satélite"
                : "Cartographic illustration; not a satellite result"
            }
          >
            <path
              d="M270 0L245 66 288 130 235 188 274 254 220 319 257 390 205 500H500V0Z"
              fill="#c0d8dc"
            />
            <path
              d="M82 80L238 65 317 182 272 347 111 382 40 229Z"
              fill="#128777"
              fillOpacity=".15"
              stroke="#128777"
              strokeWidth="2"
              strokeDasharray="8 4"
            />
            <path
              d="M77 83L160 160 95 240 173 326 111 380M160 160L238 65M160 160L250 240 317 182M95 240L250 240 272 347"
              fill="none"
              stroke="#91b49d"
              strokeWidth="1"
            />
            <circle
              cx="173"
              cy="230"
              r="7"
              fill="#128777"
              stroke="white"
              strokeWidth="3"
            />
          </svg>
          <div className="map-stamp">
            <Satellite size={20} />
            <div>
              <strong>MAPUTO, MOZAMBIQUE</strong>
              <small>25.95° S · 32.57° E</small>
            </div>
          </div>
          <div className="map-note">
            {locale === "pt"
              ? "ILUSTRAÇÃO CARTOGRÁFICA"
              : "CARTOGRAPHIC ILLUSTRATION"}
          </div>
        </div>
      </section>
      <section className="feature-grid">
        {[
          [Satellite, t.features1, t.features1Text],
          [ScanLine, t.features2, t.features2Text],
          [FileStack, t.features3, t.features3Text],
        ].map(([Icon, title, text], i) => {
          const I = Icon as typeof Satellite;
          return (
            <article key={i}>
              <I size={24} />
              <h2>{title as string}</h2>
              <p>{text as string}</p>
            </article>
          );
        })}
      </section>
      <footer>
        <Brand />
        <span>{t.about}</span>
        <a href="/api/openapi.json" target="_blank" rel="noreferrer">
          {t.documentation}
        </a>
      </footer>
    </main>
  );
}
