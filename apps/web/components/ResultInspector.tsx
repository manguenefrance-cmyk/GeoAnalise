"use client";
import { BarChart3, Download, FileJson, Info, Layers3 } from "lucide-react";
import type { Analysis } from "@/lib/api";
import { downloadArtifact } from "@/lib/api";
import { useApp } from "@/lib/context";
export default function ResultInspector({
  result,
  opacity,
  setOpacity,
  onError,
}: {
  result: Analysis | undefined;
  opacity: number;
  setOpacity: (n: number) => void;
  onError: (code: string) => void;
}) {
  const { t, token, errorText, locale } = useApp();
  const stats =
    (result?.stats.bands as Record<string, unknown>[] | undefined)?.[0] ||
    result?.stats;
  const histogram = stats?.histogram as
    { counts: number[]; edges: number[] } | undefined;
  const prov = result?.provenance;
  const variance = (prov?.model as Record<string, unknown>)
    ?.explained_variance_ratio as number[] | undefined;
  const percentile = stats?.percentiles as number[] | undefined;
  const num = (value: unknown) =>
    typeof value === "number" ? value.toFixed(4) : "—";
  return (
    <aside className="inspector">
      <div className="inspector-heading">
        <span>
          <BarChart3 size={16} />
          {t.inspector}
        </span>
      </div>
      {!result || result.status !== "succeeded" ? (
        <div className="empty-inspector">
          <div className="empty-orbit">
            <Layers3 size={30} />
          </div>
          <h3>{t.inspector}</h3>
          <p>{t.emptyInspector}</p>
          <div className="inspector-placeholder">
            <span />
            <span />
            <span />
            <span />
          </div>
          <small>
            <Info size={14} />
            {t.inspectorHelp}
          </small>
        </div>
      ) : (
        <>
          <div className="result-heading">
            <span className="eyebrow">{t.resultLayer}</span>
            <h2>{result.operation_id}</h2>
            <p className="microcopy">
              {prov?.sensor === "landsat-8-9" ? "Landsat 8/9" : "Sentinel-2"}
              {" · "}
              {String(prov?.resolution_m)} m
            </p>
            <span className="badge success">{t.succeeded}</span>
            {Boolean(prov?.sample) && (
              <div className="sample-label">{t.sample}</div>
            )}
          </div>
          <section className="inspector-section">
            <label>
              {t.opacity}
              <span>{Math.round(opacity * 100)}%</span>
              <input
                aria-label={t.opacity}
                type="range"
                min="0"
                max="1"
                step=".05"
                value={opacity}
                onChange={(e) => setOpacity(+e.target.value)}
              />
            </label>
            {result.stats.bands ? (
              <p className="microcopy">{t.multiBand}</p>
            ) : (
              <>
                <div className="legend-gradient" />
                <div className="legend-values">
                  <span>{num(percentile?.[0])}</span>
                  <span>{num(percentile?.[3])}</span>
                </div>
                <p className="microcopy">{t.scaleNote}</p>
              </>
            )}
          </section>
          <section className="inspector-section">
            <div className="section-label">
              {t.valid}
              <strong>
                {stats
                  ? ((stats.valid_fraction as number) * 100).toFixed(1)
                  : "—"}
                %
              </strong>
            </div>
            <div className="stat-grid">
              {[
                [t.minimum, stats?.min],
                [t.maximum, stats?.max],
                [t.mean, stats?.mean],
                [t.std, stats?.std],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <span>{label as string}</span>
                  <strong>{num(value)}</strong>
                </div>
              ))}
            </div>
          </section>
          {histogram && (
            <section className="inspector-section">
              <h3>{t.histogram}</h3>
              <div
                className="histogram"
                role="img"
                aria-label={`${t.histogram}: ${histogram.counts.join(", ")}`}
              >
                {histogram.counts.map((count, i) => (
                  <span
                    key={i}
                    title={`${histogram.edges[i]?.toFixed(3)}: ${count}`}
                    style={{
                      height: `${Math.max(2, (count / Math.max(...histogram.counts)) * 100)}%`,
                    }}
                  />
                ))}
              </div>
            </section>
          )}
          {variance && (
            <section className="inspector-section">
              <h3>{t.explainVariance}</h3>
              {variance.map((v, i) => (
                <div className="variance" key={i}>
                  <span>PC{i + 1}</span>
                  <progress max="1" value={v} />
                  <strong>{(v * 100).toFixed(2)}%</strong>
                </div>
              ))}
            </section>
          )}
          <section className="inspector-section">
            <h3>{t.provenance}</h3>
            <dl>
              {[
                [t.resolution, `${prov?.resolution_m} m`],
                [t.crs, prov?.crs],
                [t.acquisition, String(prov?.acquired_at || "").slice(0, 10)],
                [t.version, prov?.algorithm_version],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <dt>{String(label)}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
            {((prov?.warnings || []) as string[]).map((w) => (
              <p className="notice" key={w}>
                {errorText(w)}
              </p>
            ))}
          </section>
          <section className="inspector-section">
            <h3>{t.exports}</h3>
            {["cog", "png", "pdf", "json"].map((kind) => {
              const art = result.artifacts.find(
                (a) =>
                  a.artifact_type ===
                  (kind === "png" || kind === "pdf"
                    ? `${kind}-${locale}`
                    : kind),
              );
              return (
                art && (
                  <button
                    key={kind}
                    className="export-row"
                    onClick={() =>
                      downloadArtifact(art, token).catch((e) =>
                        onError(e.message),
                      )
                    }
                  >
                    {kind === "json" ? (
                      <FileJson size={16} />
                    ) : (
                      <Download size={16} />
                    )}
                    <span>
                      {kind === "cog"
                        ? "Cloud Optimized GeoTIFF"
                        : kind.toUpperCase()}
                    </span>
                    <small>{(art.bytes / 1024).toFixed(0)} KB</small>
                  </button>
                )
              );
            })}
          </section>
          <details className="inspector-section">
            <summary>{t.showJson}</summary>
            <pre>{JSON.stringify(prov, null, 2)}</pre>
          </details>
        </>
      )}
    </aside>
  );
}
