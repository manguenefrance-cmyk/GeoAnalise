"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Activity,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Download,
  FlaskConical,
  Folder,
  FolderPlus,
  Globe2,
  LayoutDashboard,
  LogOut,
  Map,
  MapPin,
  Play,
  Plus,
  RefreshCw,
  Satellite,
  ScanLine,
  Search,
  Settings,
  SlidersHorizontal,
  Sprout,
  Upload,
  X,
} from "lucide-react";
import Brand from "./Brand";
import packageInfo from "../package.json";
import ResultInspector from "./ResultInspector";
import { useApp } from "@/lib/context";
import { categoryPt } from "@/lib/i18n";
import {
  api,
  downloadArtifact,
  type Analysis,
  type Area,
  type Index,
  type Project,
  type Scene,
  type Usage,
} from "@/lib/api";

const GeoMap = dynamic(() => import("./GeoMap"), {
  ssr: false,
  loading: () => (
    <div className="map-loading">
      <RefreshCw className="spin" />
    </div>
  ),
});
const tools = ["area", "imagery", "indices", "transforms", "results"] as const;
const icons = [MapPin, Satellite, Sprout, SlidersHorizontal, BarChart3];
type Tool = (typeof tools)[number];
type View = "dashboard" | "projects" | "workspace" | "exports" | "settings";

export default function Workbench() {
  const {
    t,
    token,
    setToken,
    mode,
    locale,
    setLocale,
    online,
    errorText,
    sessionReady,
  } = useApp();
  const router = useRouter();
  const path = usePathname();
  const routeProjectId = path.match(/\/projects\/([^/]+)\/workspace/)?.[1];
  const routeJobId = path.match(/\/jobs\/([^/]+)/)?.[1];
  const view: View =
    path.includes("/workspace") || routeJobId
      ? "workspace"
      : path.endsWith("/exports")
        ? "exports"
        : path.endsWith("/settings")
          ? "settings"
          : path.endsWith("/projects") || path.endsWith("/new")
            ? "projects"
            : "dashboard";
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [areas, setAreas] = useState<Area[]>([]);
  const [areaId, setAreaId] = useState("");
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [catalog, setCatalog] = useState<Index[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [dataReady, setDataReady] = useState(false);
  const [summary, setSummary] = useState<{
    project_count: number;
    completed_analyses: number;
    active_jobs: number;
  } | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [sceneId, setSceneId] = useState("");
  const [tool, setTool] = useState<Tool>("area");
  const [indexId, setIndexId] = useState("NDVI");
  const [category, setCategory] = useState("");
  const [searchIndex, setSearchIndex] = useState("");
  const [selectedResult, setSelectedResult] = useState("");
  const [opacity, setOpacity] = useState(0.85);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [newProject, setNewProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<number[][]>([]);
  const [geojson, setGeojson] = useState("");
  const [areaName, setAreaName] = useState("");
  const [cloudMask, setCloudMask] = useState(true);
  const [startDate, setStartDate] = useState(() =>
    new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10),
  );
  const [endDate, setEndDate] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [provider, setProvider] = useState("earthsearch_c1");
  const [sensor, setSensor] = useState<"sentinel-2" | "landsat-8-9">(
    "sentinel-2",
  );
  const [bandLabels, setBandLabels] = useState<Record<string, string>>({});
  const [cloud, setCloud] = useState(20);
  const [operation, setOperation] = useState("band_ratio");
  const [numerator, setNumerator] = useState("B08");
  const [denominator, setDenominator] = useState("B04");
  const [selectedBands, setSelectedBands] = useState(["B04", "B03", "B02"]);
  const [standardize, setStandardize] = useState(false);
  const [earlier, setEarlier] = useState("");
  const [later, setLater] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [saved, setSaved] = useState(false);
  const [deletionStatus, setDeletionStatus] = useState("none");
  const [inspectorMobile, setInspectorMobile] = useState(false);
  const project = projects.find((p) => p.id === projectId);
  const area = areas.find((a) => a.id === areaId);
  const result = analyses.find((a) => a.id === selectedResult);
  const index = catalog.find((i) => i.id === indexId);
  const currentAnalyses = analyses.filter((a) => a.project_id === projectId);
  const activeJobs = analyses.filter((a) =>
    ["queued", "running"].includes(a.status),
  );
  const completed = analyses.filter((a) => a.status === "succeeded");
  const refresh = useCallback(async () => {
    if (!token) return;
    const [ps, as, us, ss, ds] = await Promise.all([
      api<Project[]>("/v1/projects", token),
      api<Analysis[]>("/v1/analyses", token),
      api<Usage>("/v1/usage", token),
      api<Scene[]>("/v1/scenes", token),
      api<{
        project_count: number;
        completed_analyses: number;
        active_jobs: number;
      }>("/v1/dashboard", token),
    ]);
    setProjects(ps);
    setAnalyses(as);
    setUsage(us);
    setScenes(ss);
    setSummary(ds);
    setDataReady(true);
    const jobAnalysis = routeJobId
      ? as.find((a) => a.job.id === routeJobId)
      : undefined;
    if (jobAnalysis) {
      setSelectedResult(jobAnalysis.id);
      setTool("results");
    }
    setProjectId(
      (current) =>
        jobAnalysis?.project_id ||
        (ps.some((p) => p.id === routeProjectId)
          ? routeProjectId!
          : ps.some((p) => p.id === current)
            ? current
            : ps[0]?.id || ""),
    );
  }, [token, routeProjectId, routeJobId]);
  const visibleScenes = scenes.filter((s) => s.sensor === sensor);
  const sensorLabel =
    sensor === "sentinel-2"
      ? "Sentinel-2 Level-2A"
      : "Landsat 8/9 Collection 2 Level-2";
  function changeSensor(value: "sentinel-2" | "landsat-8-9") {
    setSensor(value);
    setProvider(
      value === "sentinel-2" ? "earthsearch_c1" : "planetary_computer",
    );
    setSceneId("");
    setIndexId("NDVI");
    setCategory("");
    setSelectedBands(["B04", "B03", "B02"]);
    setNumerator("B08");
    setDenominator("B04");
    setNotice("");
  }
  useEffect(() => {
    if (!token) return;
    let current = true;
    setCatalog([]);
    setBandLabels({});
    api<{ indices: Index[]; native_bands: Record<string, string> }>(
      `/v1/indices?sensor=${sensor}`,
      token,
    )
      .then((value) => {
        if (current) {
          setCatalog(value.indices);
          setBandLabels(value.native_bands);
        }
      })
      .catch((error) => {
        if (current) setError(error.message);
      });
    return () => {
      current = false;
    };
  }, [sensor, token]);
  useEffect(() => {
    if (!newProject) return;
    const previous = document.activeElement as HTMLElement | null;
    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNewProject(false);
        return;
      }
      if (event.key !== "Tab") return;
      const controls = Array.from(
        document.querySelectorAll<HTMLElement>(
          ".modal button:not(:disabled), .modal input, .modal textarea",
        ),
      );
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, [newProject]);
  useEffect(() => {
    if (token) {
      void refresh().catch((e) => setError(e.message));
      api<{ display_name: string }>("/v1/me", token)
        .then((p) => setDisplayName(p.display_name))
        .catch(() => {});
      api<{ status: string }>("/v1/me/deletion-request", token)
        .then((value) => setDeletionStatus(value.status))
        .catch(() => {});
    }
  }, [token, refresh]);
  useEffect(() => {
    if (!token || !projectId) {
      setAreas([]);
      return;
    }
    api<Area[]>(`/v1/projects/${projectId}/aois`, token)
      .then((a) => {
        setAreas(a);
        setAreaId((current) =>
          a.some((x) => x.id === current) ? current : a[0]?.id || "",
        );
      })
      .catch((e) => setError(e.message));
  }, [projectId, token]);
  useEffect(() => {
    if (!activeJobs.length) return;
    const id = setInterval(() => {
      void refresh().catch((e) => setError(e.message));
    }, 3000);
    return () => clearInterval(id);
  }, [activeJobs.length, refresh]);
  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "UNKNOWN_ERROR");
    } finally {
      setBusy(false);
    }
  }
  function openProject(p: Project) {
    setProjectId(p.id);
    setSelectedResult("");
    setPoints([]);
    setDrawing(false);
    router.push(`/app/projects/${p.id}/workspace`);
  }
  async function seed() {
    await act(async () => {
      const data = await api<{ project: Project; scenes: Scene[] }>(
        "/v1/test/seed",
        token,
        { method: "POST" },
      );
      await refresh();
      changeSensor("sentinel-2");
      setProjectId(data.project.id);
      setScenes(data.scenes);
      setSceneId(data.scenes[0].id);
      setTool("indices");
      router.push(`/app/projects/${data.project.id}/workspace`);
    });
  }
  async function createProject(e: FormEvent) {
    e.preventDefault();
    await act(async () => {
      const p = await api<Project>("/v1/projects", token, {
        method: "POST",
        body: JSON.stringify({
          name: projectName,
          description: projectDescription,
        }),
      });
      await refresh();
      setNewProject(false);
      setProjectName("");
      setProjectDescription("");
      setTool("area");
      openProject(p);
    });
  }
  async function saveArea() {
    await act(async () => {
      let geometry: unknown;
      if (points.length >= 3)
        geometry = { type: "Polygon", coordinates: [[...points, points[0]]] };
      else {
        const parsed = JSON.parse(geojson);
        geometry = parsed.geometry || parsed;
      }
      const a = await api<Area>(`/v1/projects/${projectId}/aois`, token, {
        method: "POST",
        body: JSON.stringify({ name: areaName || t.area, geometry }),
      });
      setAreas((old) => [...old, a]);
      setAreaId(a.id);
      setPoints([]);
      setDrawing(false);
      setGeojson("");
      setTool("imagery");
    });
  }
  async function importArea(file: File) {
    await act(async () => {
      const data = new FormData();
      data.append("file", file);
      const a = await api<Area>(
        `/v1/projects/${projectId}/aois/import`,
        token,
        { method: "POST", body: data },
      );
      setAreas((old) => [...old, a]);
      setAreaId(a.id);
      setTool("imagery");
    });
  }
  async function searchScenes() {
    await act(async () => {
      const data = await api<{ scenes: Scene[] }>(
        "/v1/satellite/search",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            aoi_id: areaId,
            provider,
            sensor,
            date_start: startDate,
            date_end: endDate,
            max_cloud_cover: cloud,
            limit: 20,
          }),
        },
      );
      setScenes(data.scenes);
      setSceneId(data.scenes[0]?.id || "");
      if (!data.scenes.length) setNotice(t.noScenes);
    });
  }
  async function runAnalysis(retry?: Analysis) {
    await act(async () => {
      const kind =
        retry?.operation_kind || (tool === "indices" ? "index" : operation);
      const id =
        retry?.operation_id ||
        (kind === "index"
          ? indexId
          : kind === "band_ratio"
            ? "BAND_RATIO"
            : kind === "pca"
              ? "PCA"
              : kind === "composite"
                ? "RGB"
                : "TEMPORAL_DIFFERENCE");
      const params = retry?.params || {
        cloud_mask: cloudMask,
        ...(kind === "band_ratio" ? { numerator, denominator } : {}),
        ...(["pca", "composite"].includes(kind)
          ? { bands: selectedBands, standardize }
          : {}),
      };
      const data = await api<Analysis>("/v1/analyses", token, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          project_id: retry?.project_id || projectId,
          aoi_id: retry?.aoi_id || areaId,
          scene_id:
            kind === "temporal_diff" ? null : retry?.scene_id || sceneId,
          operation_kind: kind,
          operation_id: id,
          params,
          input_analysis_ids:
            retry?.input_analysis_ids ||
            (kind === "temporal_diff" ? [earlier, later] : []),
        }),
      });
      await refresh();
      setSelectedResult(data.id);
      setTool("results");
    });
  }
  async function projectAction(action: string) {
    if (!project) return;
    if (action === "delete" && !confirm(t.deleteConfirm)) return;
    await act(async () => {
      if (action === "delete")
        await api(`/v1/projects/${project.id}`, token, { method: "DELETE" });
      else if (action === "rename") {
        const name = prompt(t.name, project.name);
        if (!name) return;
        await api(`/v1/projects/${project.id}`, token, {
          method: "PATCH",
          body: JSON.stringify({ name }),
        });
      } else
        await api(`/v1/projects/${project.id}`, token, {
          method: "PATCH",
          body: JSON.stringify({ status: "archived" }),
        });
      await refresh();
      setNotice(t.changed);
      if (action === "delete") router.push("/app/projects");
    });
  }
  const date = (v: string) =>
    new Date(v).toLocaleDateString(locale === "pt" ? "pt-MZ" : "en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  const runDisabled =
    !catalog.length ||
    busy ||
    !areaId ||
    (tool === "transforms" && operation === "temporal_diff"
      ? !earlier || !later
      : !sceneId);

  if (!sessionReady)
    return (
      <main className="auth-page" aria-busy="true">
        <Brand />
        <p role="status">{t.loading}</p>
      </main>
    );
  if (!token)
    return (
      <main className="auth-page">
        <Brand />
        <section className="auth-card">
          <div className="eyebrow">{t.privateWorkspace}</div>
          <h1>{t.explore}</h1>
          <p>{t.intro}</p>
          <Link href="/auth/login" className="button primary full">
            {t.login}
          </Link>
          {mode === "test" && (
            <button
              className="button secondary full"
              onClick={() => setToken("test:demo")}
            >
              <FlaskConical size={18} />
              {t.testLogin}
            </button>
          )}
        </section>
      </main>
    );
  return (
    <div
      className={`app-shell ${view === "workspace" ? "workspace-mode" : ""}`}
    >
      <aside className="main-rail">
        <Brand compact />
        <nav>
          {(
            [
              ["dashboard", LayoutDashboard],
              ["projects", Folder],
              ["workspace", Map],
              ["exports", Download],
              ["settings", Settings],
            ] as const
          ).map(([item, Icon]) => (
            <button
              key={item}
              className={view === item ? "active" : ""}
              title={t[item === "dashboard" ? "overview" : item]}
              aria-label={t[item === "dashboard" ? "overview" : item]}
              onClick={() =>
                item === "workspace"
                  ? project
                    ? openProject(project)
                    : router.push("/app/projects")
                  : router.push(`/app/${item}`)
              }
            >
              <Icon size={22} />
              <span>{t[item === "dashboard" ? "overview" : item]}</span>
            </button>
          ))}
        </nav>
        <div className="rail-bottom">
          <a
            title={t.documentation}
            aria-label={t.documentation}
            href="/api/openapi.json"
            target="_blank"
            rel="noreferrer"
          >
            <CircleHelp size={21} />
          </a>
          <button
            title={t.logout}
            aria-label={t.logout}
            onClick={() => {
              setToken("");
              router.push("/auth/login");
            }}
          >
            <LogOut size={20} />
          </button>
          <div className="avatar">
            {displayName.slice(0, 2).toUpperCase() || "GA"}
          </div>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <div className="breadcrumb">
            <span>GeoAnalytics</span>
            <ChevronRight size={14} />
            <strong>
              {view === "workspace"
                ? project?.name || t.workspace
                : t[view === "dashboard" ? "overview" : view]}
            </strong>
            {view === "workspace" && <span className="badge beta">BETA</span>}
          </div>
          <div className="header-actions">
            {mode === "test" && (
              <span className="test-badge">
                <FlaskConical size={13} />
                {t.testMode}
              </span>
            )}
            <button
              className="locale-toggle"
              onClick={() => setLocale(locale === "en" ? "pt" : "en")}
              aria-label={t.language}
            >
              <Globe2 size={15} />
              {locale.toUpperCase()}
              <ChevronDown size={12} />
            </button>
            <span
              className={`connection ${online ? "online" : ""}`}
              title={online ? t.healthy : t.offline}
            />
            <span className="header-profile">
              {displayName || t.privateWorkspace}
            </span>
          </div>
        </header>
        {(error || notice) && (
          <div
            role={error ? "alert" : "status"}
            className={`global-message ${error ? "error" : "success"}`}
          >
            <span>{error ? errorText(error) : notice}</span>
            <button
              aria-label={t.cancel}
              onClick={() => {
                setError("");
                setNotice("");
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {view === "workspace" ? (
          <>
            <div className="workspace-toolbar">
              <div className="project-picker">
                <Folder size={16} />
                <select
                  aria-label={t.activeProject}
                  value={projectId}
                  onChange={(e) => {
                    const p = projects.find((x) => x.id === e.target.value);
                    if (p) openProject(p);
                  }}
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="workspace-toolbar-right">
                <span className="quota-mini">
                  <Activity size={14} />
                  {usage
                    ? usage.daily_limit - usage.settled - usage.reserved
                    : 0}{" "}
                  {t.remaining}
                </span>
                <button
                  className="icon-button"
                  aria-label={t.refresh}
                  onClick={() => void act(refresh)}
                >
                  <RefreshCw size={16} />
                </button>
                <button
                  className="inspector-toggle"
                  onClick={() => setInspectorMobile(!inspectorMobile)}
                >
                  <BarChart3 size={17} />
                  {t.inspector}
                </button>
              </div>
            </div>
            <div className="workspace-layout">
              <section className="tool-panel">
                <div className="tool-tabs" role="tablist">
                  {tools.map((id, i) => {
                    const Icon = icons[i];
                    return (
                      <button
                        role="tab"
                        aria-selected={tool === id}
                        title={t[id]}
                        aria-label={t[id]}
                        className={tool === id ? "active" : ""}
                        key={id}
                        onClick={() => setTool(id)}
                      >
                        <Icon size={19} />
                        <span>
                          {
                            [
                              t.toolArea,
                              t.toolImagery,
                              t.toolIndices,
                              t.toolTransforms,
                              t.toolResults,
                            ][i]
                          }
                        </span>
                      </button>
                    );
                  })}
                </div>
                <div className="panel-scroll">
                  <div className="panel-title">
                    <span className="eyebrow">GEOANALYTICS</span>
                    <h1>{t[tool]}</h1>
                  </div>
                  {tool !== "results" && (
                    <label>
                      {locale === "pt" ? "Satélite" : "Satellite"}
                      <select
                        value={sensor}
                        onChange={(e) =>
                          changeSensor(e.target.value as typeof sensor)
                        }
                      >
                        <option value="sentinel-2">
                          Sentinel-2 · {locale === "pt" ? "padrão" : "default"}
                        </option>
                        <option value="landsat-8-9">Landsat 8/9 · 30 m</option>
                      </select>
                    </label>
                  )}
                  {sensor === "landsat-8-9" && tool === "indices" && (
                    <p className="microcopy">
                      {locale === "pt"
                        ? "19 índices compatíveis. Os índices red-edge exigem Sentinel-2."
                        : "19 compatible indices. Red-edge indices require Sentinel-2."}
                    </p>
                  )}
                  {tool === "area" && (
                    <>
                      <p className="panel-description">{t.areaHelp}</p>
                      {areas.length > 0 && (
                        <label>
                          {t.area}
                          <select
                            value={areaId}
                            onChange={(e) => setAreaId(e.target.value)}
                          >
                            {areas.map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.name} · {a.area_km2.toFixed(3)} km²
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      {area && (
                        <div className="area-summary">
                          <MapPin size={21} />
                          <div>
                            <strong>
                              {area.area_km2.toFixed(3)} <small>km²</small>
                            </strong>
                            <span>{area.name}</span>
                          </div>
                          <span className="badge success">WGS 84</span>
                        </div>
                      )}
                      <div className="drawing-actions">
                        <button
                          className="button primary full"
                          disabled={!projectId}
                          onClick={() => {
                            if (drawing) {
                              setDrawing(false);
                              if (points.length >= 3)
                                setGeojson(
                                  JSON.stringify(
                                    {
                                      type: "Polygon",
                                      coordinates: [[...points, points[0]]],
                                    },
                                    null,
                                    2,
                                  ),
                                );
                            } else {
                              setPoints([]);
                              setDrawing(true);
                            }
                          }}
                        >
                          <ScanLine size={17} />
                          {drawing ? t.finish : t.draw}
                        </button>
                        {points.length > 0 && (
                          <button
                            className="text-button"
                            onClick={() => {
                              setPoints([]);
                              setDrawing(false);
                              setGeojson("");
                            }}
                          >
                            {t.clear}
                          </button>
                        )}
                      </div>
                      {drawing && <p className="notice">{t.drawHelp}</p>}
                      <label className="file-import">
                        <Upload size={17} />
                        {t.importArea}
                        <input
                          type="file"
                          accept=".json,.geojson,.zip"
                          disabled={busy || !projectId}
                          onChange={(e) => {
                            if (e.target.files?.[0])
                              void importArea(e.target.files[0]);
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <div className="divider-label">{t.coordinates}</div>
                      <label>
                        {t.areaName}
                        <input
                          value={areaName}
                          onChange={(e) => setAreaName(e.target.value)}
                          placeholder={t.area}
                        />
                      </label>
                      <label>
                        {t.geojson}
                        <textarea
                          rows={5}
                          value={geojson}
                          onChange={(e) => {
                            setGeojson(e.target.value);
                            setPoints([]);
                          }}
                          placeholder={'{"type":"Polygon","coordinates":[…]}'}
                        />
                      </label>
                      <button
                        className="button secondary full"
                        disabled={
                          busy || !projectId || (!geojson && points.length < 3)
                        }
                        onClick={() => void saveArea()}
                      >
                        <Check size={16} />
                        {t.saveArea}
                      </button>
                      <p className="microcopy">
                        <CircleHelp size={13} />
                        {t.maxArea}
                      </p>
                      {mode === "test" && (
                        <button
                          className="test-fixture-button"
                          disabled={busy}
                          onClick={() => void seed()}
                        >
                          <FlaskConical size={17} />
                          {t.testSeed}
                        </button>
                      )}
                    </>
                  )}
                  {tool === "imagery" && (
                    <>
                      <p className="panel-description">
                        {sensorLabel} · {t.sourceNotice}
                      </p>
                      {!area && <p className="notice">{t.noArea}</p>}
                      <label>
                        {t.provider}
                        <select
                          value={provider}
                          onChange={(e) => setProvider(e.target.value)}
                        >
                          {sensor === "sentinel-2" ? (
                            <>
                              <option value="earthsearch_c1">
                                Earth Search · Sentinel-2 Collection 1
                              </option>
                              <option value="copernicus">
                                Copernicus Data Space
                              </option>
                            </>
                          ) : (
                            <option value="planetary_computer">
                              Microsoft Planetary Computer · Landsat
                            </option>
                          )}
                        </select>
                      </label>
                      <div className="form-two">
                        <label>
                          {t.startDate}
                          <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                          />
                        </label>
                        <label>
                          {t.endDate}
                          <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                          />
                        </label>
                      </div>
                      <label className="range-label">
                        {t.cloud}
                        <strong>≤ {cloud}%</strong>
                        <input
                          aria-label={t.cloud}
                          type="range"
                          value={cloud}
                          min="0"
                          max="100"
                          onChange={(e) => setCloud(+e.target.value)}
                        />
                      </label>
                      <button
                        className="button primary full"
                        disabled={!areaId || busy}
                        onClick={() => void searchScenes()}
                      >
                        <Search size={16} />
                        {busy ? t.loading : t.search}
                      </button>
                      <div className="divider-label">
                        {visibleScenes.length} {t.imagery.toLowerCase()}
                      </div>
                      {!visibleScenes.length && (
                        <div className="empty-small">
                          <Satellite size={26} />
                          <p>{t.noScenes}</p>
                        </div>
                      )}
                      {visibleScenes.map((s) => (
                        <button
                          className={`scene-card ${sceneId === s.id ? "selected" : ""}`}
                          key={s.id}
                          onClick={() => {
                            setSceneId(s.id);
                            setTool("indices");
                          }}
                        >
                          <div className="scene-symbol">
                            <Satellite size={22} />
                            <span>
                              {s.sensor === "sentinel-2" ? "S2" : "L8/9"}
                            </span>
                          </div>
                          <div>
                            <strong>
                              {String(s.properties.datetime).slice(0, 10)}
                            </strong>
                            <small>
                              {String(s.properties["eo:cloud_cover"] ?? "—")}%{" "}
                              {t.sceneCloud}
                            </small>
                            <span className="scene-id">{s.stac_item_id}</span>
                            {s.sample && (
                              <span className="sample-label">{t.sample}</span>
                            )}
                            <small>
                              {s.asset_keys.length}{" "}
                              {t.availableAssets.toLowerCase()}
                            </small>
                          </div>
                          {sceneId === s.id && <Check size={16} />}
                        </button>
                      ))}
                      {mode === "test" && (
                        <button
                          className="test-fixture-button"
                          disabled={busy}
                          onClick={() => void seed()}
                        >
                          <FlaskConical size={17} />
                          {t.testSeed}
                        </button>
                      )}
                    </>
                  )}
                  {tool === "indices" && (
                    <>
                      <p className="panel-description">{t.proxy}</p>
                      <div className="search-input">
                        <Search size={16} />
                        <input
                          aria-label={t.findIndex}
                          placeholder={t.findIndex}
                          value={searchIndex}
                          onChange={(e) => setSearchIndex(e.target.value)}
                        />
                      </div>
                      <select
                        aria-label={t.category}
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                      >
                        <option value="">{t.all}</option>
                        {[...new Set(catalog.map((i) => i.category))].map(
                          (c) => (
                            <option key={c} value={c}>
                              {locale === "pt" ? categoryPt[c] : c}
                            </option>
                          ),
                        )}
                      </select>
                      <div className="index-list">
                        {catalog
                          .filter(
                            (i) =>
                              (!category || i.category === category) &&
                              `${i.id} ${i.title}`
                                .toLowerCase()
                                .includes(searchIndex.toLowerCase()),
                          )
                          .map((i) => (
                            <button
                              className={i.id === indexId ? "selected" : ""}
                              onClick={() => setIndexId(i.id)}
                              key={i.id}
                            >
                              <span className="index-icon">
                                <Sprout size={17} />
                              </span>
                              <span>
                                <strong>{i.id}</strong>
                                <small>
                                  {locale === "pt"
                                    ? categoryPt[i.category]
                                    : i.category}{" "}
                                  · {i.native_output_resolution_m} m
                                </small>
                              </span>
                              {i.id === indexId ? (
                                <Check size={16} />
                              ) : (
                                <ChevronRight size={14} />
                              )}
                            </button>
                          ))}
                      </div>
                      {index && (
                        <div className="formula-card">
                          <span className="eyebrow">
                            {t.formula} / {index.id}
                          </span>
                          <p>
                            {locale === "pt" ? index.title_pt : index.title}
                          </p>
                          <code>{index.formula}</code>
                          <div>
                            <span>{t.bands}</span>
                            <strong>{index.bands.join(" + ")}</strong>
                          </div>
                          <p>
                            {locale === "pt" ? index.notes_pt : index.notes}
                          </p>
                          <div>
                            <span>{t.native}</span>
                            <strong>
                              {index.native_output_resolution_m} m
                            </strong>
                          </div>
                          {["NDWI_MCF", "NDMI", "NDSI_SNOW", "MNDWI"].includes(
                            index.id,
                          ) && (
                            <p>
                              {index.id === "NDWI_MCF"
                                ? "McFeeters · Green / NIR"
                                : index.id === "NDMI"
                                  ? "Gao · NIR / SWIR"
                                  : locale === "pt"
                                    ? "MNDWI e NDSI_SNOW partilham a fórmula; a interpretação depende do contexto."
                                    : "MNDWI and NDSI_SNOW share algebra; interpretation depends on context."}
                            </p>
                          )}
                        </div>
                      )}
                      <label>
                        {t.selectedScene}
                        <select
                          value={sceneId}
                          onChange={(e) => setSceneId(e.target.value)}
                        >
                          <option value="">{t.chooseScene}</option>
                          {visibleScenes.map((s) => (
                            <option key={s.id} value={s.id}>
                              {String(s.properties.datetime).slice(0, 10)} ·{" "}
                              {s.stac_item_id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={cloudMask}
                          onChange={(e) => setCloudMask(e.target.checked)}
                        />
                        {sensor === "sentinel-2"
                          ? t.cloudMask
                          : locale === "pt"
                            ? "Mascarar nuvens, sombras e neve (QA_PIXEL)"
                            : "Mask clouds, shadows and snow (QA_PIXEL)"}
                      </label>
                      <button
                        className="button primary full"
                        disabled={runDisabled}
                        onClick={() => void runAnalysis()}
                      >
                        <Play size={16} />
                        {busy ? t.loading : t.run}
                      </button>
                      <p className="microcopy centered">{t.cost}</p>
                    </>
                  )}
                  {tool === "transforms" && (
                    <>
                      <label>
                        {t.method}
                        <select
                          value={operation}
                          onChange={(e) => setOperation(e.target.value)}
                        >
                          <option value="band_ratio">{t.ratio}</option>
                          <option value="temporal_diff">{t.temporal}</option>
                          <option value="pca">{t.pca}</option>
                          <option value="composite">{t.composite}</option>
                        </select>
                      </label>
                      {operation === "band_ratio" && (
                        <>
                          <div className="formula-card">
                            <code>ρ(A) / ρ(B)</code>
                          </div>
                          <div className="form-two">
                            {[
                              ["numerator", numerator, setNumerator],
                              ["denominator", denominator, setDenominator],
                            ].map(([label, value, set]) => (
                              <label key={label as string}>
                                {t[label as "numerator"]}
                                <select
                                  value={value as string}
                                  onChange={(e) =>
                                    (set as (s: string) => void)(e.target.value)
                                  }
                                >
                                  {Object.keys(bandLabels).map((b) => (
                                    <option key={b} value={b}>
                                      {bandLabels[b]}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            ))}
                          </div>
                        </>
                      )}
                      {operation === "temporal_diff" ? (
                        <>
                          <p className="panel-description">{t.temporalHelp}</p>
                          {[
                            [t.earlier, earlier, setEarlier],
                            [t.later, later, setLater],
                          ].map(([label, value, set]) => (
                            <label key={label as string}>
                              {label as string}
                              <select
                                value={value as string}
                                onChange={(e) =>
                                  (set as (s: string) => void)(e.target.value)
                                }
                              >
                                <option value="">—</option>
                                {completed
                                  .filter(
                                    (a) =>
                                      a.project_id === projectId &&
                                      a.aoi_id === areaId &&
                                      a.operation_kind === "index" &&
                                      (a.provenance.sensor || "sentinel-2") ===
                                        sensor,
                                  )
                                  .map((a) => (
                                    <option key={a.id} value={a.id}>
                                      {a.operation_id} ·{" "}
                                      {String(a.provenance.acquired_at).slice(
                                        0,
                                        10,
                                      )}
                                    </option>
                                  ))}
                              </select>
                            </label>
                          ))}
                        </>
                      ) : (
                        <label>
                          {t.selectedScene}
                          <select
                            value={sceneId}
                            onChange={(e) => setSceneId(e.target.value)}
                          >
                            <option value="">{t.chooseScene}</option>
                            {visibleScenes.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.stac_item_id}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      {["pca", "composite"].includes(operation) && (
                        <>
                          <p className="panel-description">
                            {operation === "pca" ? t.pcaHelp : t.scaleNote}
                          </p>
                          {operation === "composite" ? (
                            <select
                              aria-label={t.composite}
                              value={selectedBands.join(",")}
                              onChange={(e) =>
                                setSelectedBands(e.target.value.split(","))
                              }
                            >
                              <option value="B04,B03,B02">
                                RGB ·{" "}
                                {["B04", "B03", "B02"]
                                  .map((b) => bandLabels[b])
                                  .join(" / ")}
                              </option>
                              <option value="B08,B04,B03">
                                FCC ·{" "}
                                {["B08", "B04", "B03"]
                                  .map((b) => bandLabels[b])
                                  .join(" / ")}
                              </option>
                              <option value="B11,B08,B04">
                                SWIR ·{" "}
                                {["B11", "B08", "B04"]
                                  .map((b) => bandLabels[b])
                                  .join(" / ")}
                              </option>
                            </select>
                          ) : (
                            <>
                              <div className="band-checks">
                                {Object.keys(bandLabels).map((b) => (
                                  <label key={b}>
                                    <input
                                      type="checkbox"
                                      checked={selectedBands.includes(b)}
                                      onChange={(e) =>
                                        setSelectedBands((old) =>
                                          e.target.checked
                                            ? [...old, b]
                                            : old.filter((x) => x !== b),
                                        )
                                      }
                                    />
                                    {bandLabels[b]}
                                  </label>
                                ))}
                              </div>
                              <label className="checkbox">
                                <input
                                  type="checkbox"
                                  checked={standardize}
                                  onChange={(e) =>
                                    setStandardize(e.target.checked)
                                  }
                                />
                                {t.standardize}
                              </label>
                            </>
                          )}
                        </>
                      )}
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={cloudMask}
                          onChange={(e) => setCloudMask(e.target.checked)}
                        />
                        {sensor === "sentinel-2"
                          ? t.cloudMask
                          : locale === "pt"
                            ? "Mascarar nuvens, sombras e neve (QA_PIXEL)"
                            : "Mask clouds, shadows and snow (QA_PIXEL)"}
                      </label>
                      <button
                        className="button primary full"
                        disabled={
                          runDisabled ||
                          (operation === "pca" && selectedBands.length < 3)
                        }
                        onClick={() => void runAnalysis()}
                      >
                        <Play size={16} />
                        {t.run}
                      </button>
                      <p className="microcopy centered">{t.cost}</p>
                    </>
                  )}
                  {tool === "results" && (
                    <>
                      <p className="panel-description">{t.selectResult}</p>
                      {!currentAnalyses.length && (
                        <div className="empty-small">
                          <BarChart3 size={28} />
                          <p>{t.noResults}</p>
                        </div>
                      )}
                      {currentAnalyses.map((a) => (
                        <div
                          key={a.id}
                          className={`job-card ${selectedResult === a.id ? "selected" : ""}`}
                        >
                          <button
                            className="job-select"
                            onClick={() => setSelectedResult(a.id)}
                          >
                            <span className="result-symbol">
                              <BarChart3 size={20} />
                            </span>
                            <span>
                              <strong>{a.operation_id}</strong>
                              <small>
                                {date(
                                  String(
                                    a.provenance.acquired_at || a.created_at,
                                  ),
                                )}
                              </small>
                            </span>
                            <span className={`badge ${a.status}`}>
                              {t[a.status]}
                            </span>
                          </button>
                          {a.status === "failed" && (
                            <p className="notice error">
                              {errorText(
                                a.job.error_code ||
                                  "PROCESSING_FAILED_CHECK_PROVIDER_ACCESS",
                              )}
                            </p>
                          )}
                          {["queued", "running"].includes(a.status) && (
                            <button
                              className="text-button"
                              onClick={() =>
                                void act(async () => {
                                  await api(
                                    `/v1/jobs/${a.job.id}/cancel`,
                                    token,
                                    { method: "POST" },
                                  );
                                  await refresh();
                                })
                              }
                            >
                              {t.cancelJob}
                            </button>
                          )}
                          {["failed", "cancelled"].includes(a.status) && (
                            <button
                              className="text-button"
                              disabled={busy}
                              onClick={() => void runAnalysis(a)}
                            >
                              <RefreshCw size={13} />
                              {t.retry}
                            </button>
                          )}
                          {a.status === "succeeded" &&
                            Boolean(a.provenance.sample) && (
                              <span className="sample-label">{t.sample}</span>
                            )}
                        </div>
                      ))}
                    </>
                  )}
                </div>
                <div className="panel-footer">
                  <span className="status-dot" />
                  {online ? t.healthy : t.offline}
                  <span>v{packageInfo.version}</span>
                </div>
              </section>
              <GeoMap
                area={area}
                points={points}
                drawing={drawing}
                onPoint={(p) => setPoints((old) => [...old, p])}
                result={result}
                opacity={opacity}
              />
              <div
                className={`inspector-wrap ${inspectorMobile ? "show" : ""}`}
              >
                <ResultInspector
                  result={result}
                  opacity={opacity}
                  setOpacity={setOpacity}
                  onError={setError}
                />
              </div>
            </div>
            <div className="workspace-status">
              <div>
                <span className="status-dot" />
                {area
                  ? `${area.name} · ${area.area_km2.toFixed(3)} km²`
                  : t.noArea}
              </div>
              <span>
                {result?.status === "succeeded" && !result.provenance.sample
                  ? t.mapAttribution
                  : mode === "test"
                    ? t.testNotice
                    : t.mapAttribution}
              </span>
              <span>
                {activeJobs.length} {t.active.toLowerCase()}
              </span>
            </div>
          </>
        ) : (
          <main className="content-page">
            <div className="page-heading">
              <div>
                <span className="eyebrow">ARCAMBE / {t.privateWorkspace}</span>
                <h1>{view === "dashboard" ? t.dashboard : t[view]}</h1>
                <p>
                  {view === "dashboard"
                    ? t.intro
                    : view === "exports"
                      ? t.exportHelp
                      : t.about}
                </p>
              </div>
              {["dashboard", "projects"].includes(view) && (
                <button
                  className="button primary"
                  onClick={() => setNewProject(true)}
                >
                  <Plus size={17} />
                  {t.newProject}
                </button>
              )}
            </div>
            {view === "dashboard" && (
              <>
                <div className="metrics-grid">
                  {[
                    [Folder, t.projectCount, summary?.project_count ?? "—"],
                    [Check, t.successful, summary?.completed_analyses ?? "—"],
                    [Activity, t.active, summary?.active_jobs ?? "—"],
                    [
                      ScanLine,
                      t.credits,
                      usage ? `${usage.settled} / ${usage.daily_limit}` : "—",
                    ],
                  ].map(([Icon, label, value], i) => {
                    const I = Icon as typeof Folder;
                    return (
                      <article key={i}>
                        <div>
                          <I size={19} />
                          <span>{label as string}</span>
                        </div>
                        <strong>{value as string | number}</strong>
                        <span className="metric-line" />
                      </article>
                    );
                  })}
                </div>
                <div className="section-heading">
                  <h2>{t.projects}</h2>
                  <Link href="/app/projects">{t.all}</Link>
                </div>
              </>
            )}
            {["dashboard", "projects"].includes(view) && (
              <>
                {!dataReady ? (
                  <p role="status" className="muted-box">
                    {error ? t.error : t.loading}
                  </p>
                ) : !projects.length ? (
                  <div className="empty-state">
                    <div className="empty-icon">
                      <FolderPlus size={32} />
                    </div>
                    <h2>{t.noProjects}</h2>
                    <p>{t.noProjectsHelp}</p>
                    <button
                      className="button primary"
                      onClick={() => setNewProject(true)}
                    >
                      <Plus size={17} />
                      {t.newProject}
                    </button>
                    {mode === "test" && (
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() => void seed()}
                      >
                        <FlaskConical size={17} />
                        {t.testSeed}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="projects-grid">
                    {projects.map((p, i) => (
                      <article className="project-card" key={p.id}>
                        <div className={`project-thumbnail pattern-${i % 3}`}>
                          <div className="project-polygon" />
                          <span>
                            {p.status === "archived" ? t.archive : "WGS 84"}
                          </span>
                          <Folder size={23} />
                        </div>
                        <div className="project-card-body">
                          <small>{date(p.created_at)}</small>
                          <h3>{p.name}</h3>
                          <p>{p.description || t.about}</p>
                          <button onClick={() => openProject(p)}>
                            {t.openWorkspace}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
                {mode === "test" && projects.length > 0 && (
                  <button
                    className="test-fixture-button"
                    disabled={busy}
                    onClick={() => void seed()}
                  >
                    <FlaskConical size={17} />
                    {t.testSeed}
                  </button>
                )}
              </>
            )}
            {view === "dashboard" && (
              <section className="recent-section">
                <div className="section-heading">
                  <h2>{t.recent}</h2>
                  <button
                    className="text-button"
                    onClick={() => void act(refresh)}
                  >
                    <RefreshCw size={14} />
                    {t.refresh}
                  </button>
                </div>
                {!analyses.length ? (
                  <p className="muted-box">
                    <Clock3 size={18} />
                    {t.noJobs}
                  </p>
                ) : (
                  <div className="activity-table">
                    {analyses.slice(0, 6).map((a) => (
                      <button
                        key={a.id}
                        onClick={() => {
                          setProjectId(a.project_id);
                          setSelectedResult(a.id);
                          setTool("results");
                          router.push(
                            `/app/projects/${a.project_id}/workspace`,
                          );
                        }}
                      >
                        <span className="result-symbol">
                          <BarChart3 size={18} />
                        </span>
                        <strong>{a.operation_id}</strong>
                        <span>
                          {projects.find((p) => p.id === a.project_id)?.name}
                        </span>
                        <time>{date(a.created_at)}</time>
                        <span className={`badge ${a.status}`}>
                          {t[a.status]}
                        </span>
                        <ChevronRight size={16} />
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}
            {view === "exports" && (
              <>
                {!completed.length ? (
                  <div className="empty-state">
                    <Download size={35} />
                    <h2>{t.noExports}</h2>
                  </div>
                ) : (
                  completed.map((a) => (
                    <section className="export-group" key={a.id}>
                      <h2>
                        {a.operation_id}
                        <span>{date(a.created_at)}</span>
                        {Boolean(a.provenance.sample) && (
                          <small className="sample-label">{t.sample}</small>
                        )}
                      </h2>
                      {a.artifacts
                        .filter(
                          (x) =>
                            x.artifact_type !== "preview" &&
                            (!x.artifact_type.includes("-") ||
                              x.artifact_type.endsWith(locale)),
                        )
                        .map((artifact) => (
                          <button
                            className="export-row"
                            key={artifact.id}
                            onClick={() =>
                              void act(async () =>
                                downloadArtifact(artifact, token),
                              )
                            }
                          >
                            <Download size={18} />
                            <strong>
                              {artifact.artifact_type === "cog"
                                ? "Cloud Optimized GeoTIFF"
                                : artifact.artifact_type.toUpperCase()}
                            </strong>
                            <span>{(artifact.bytes / 1024).toFixed(1)} KB</span>
                          </button>
                        ))}
                    </section>
                  ))
                )}
              </>
            )}
            {view === "settings" && (
              <div className="settings-grid">
                <section className="settings-card">
                  <h2>{t.profile}</h2>
                  <label>
                    {t.displayName}
                    <input
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                    />
                  </label>
                  <label>
                    {t.language}
                    <select
                      value={locale}
                      onChange={(e) => setLocale(e.target.value as "en" | "pt")}
                    >
                      <option value="en">English</option>
                      <option value="pt">Português</option>
                    </select>
                  </label>
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        await api("/v1/me", token, {
                          method: "PATCH",
                          body: JSON.stringify({
                            display_name: displayName,
                            locale,
                          }),
                        });
                        setSaved(true);
                      })
                    }
                  >
                    {saved ? <Check size={17} /> : null}
                    {saved ? t.saved : t.save}
                  </button>
                </section>
                <section className="settings-card">
                  <h2>{t.deleteAccount}</h2>
                  {deletionStatus === "requested" ? (
                    <>
                      <p role="status" className="notice">
                        {t.deletionPending}
                      </p>
                      <button
                        className="button secondary"
                        disabled={busy}
                        onClick={() =>
                          void act(async () => {
                            const value = await api<{ status: string }>(
                              "/v1/me/deletion-request",
                              token,
                              { method: "DELETE" },
                            );
                            setDeletionStatus(value.status);
                            setNotice(t.deletionCancelled);
                          })
                        }
                      >
                        {t.cancelDeletion}
                      </button>
                    </>
                  ) : (
                    <button
                      className="button secondary danger"
                      disabled={busy}
                      onClick={() => {
                        if (confirm(t.deleteAccountConfirm))
                          void act(async () => {
                            const value = await api<{ status: string }>(
                              "/v1/me/deletion-request",
                              token,
                              { method: "POST" },
                            );
                            setDeletionStatus(value.status);
                          });
                      }}
                    >
                      {t.deleteAccount}
                    </button>
                  )}
                </section>
                <section className="settings-card">
                  <h2>{t.usage}</h2>
                  <span className="badge beta">{t.freePlan}</span>
                  <dl>
                    <div>
                      <dt>{t.attempts}</dt>
                      <dd>
                        {usage
                          ? `${usage.attempted} / ${usage.daily_attempt_limit}`
                          : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt>{t.credits}</dt>
                      <dd>
                        {usage?.settled || 0} / {usage?.daily_limit || 5}
                      </dd>
                    </div>
                    <div>
                      <dt>{t.active}</dt>
                      <dd>
                        {usage?.reserved || 0} / {usage?.concurrent_limit || 1}
                      </dd>
                    </div>
                    <div>
                      <dt>{t.area}</dt>
                      <dd>≤ {usage?.max_aoi_km2 || 100} km²</dd>
                    </div>
                  </dl>
                  <p className="microcopy">{t.billing}</p>
                </section>
                {project && (
                  <section className="settings-card">
                    <h2>{project.name}</h2>
                    <button
                      className="button secondary"
                      onClick={() => void projectAction("rename")}
                    >
                      {t.rename}
                    </button>
                    <button
                      className="text-button"
                      onClick={() => void projectAction("archive")}
                    >
                      {t.archive}
                    </button>
                    <button
                      className="text-button danger"
                      onClick={() => void projectAction("delete")}
                    >
                      {t.delete}
                    </button>
                  </section>
                )}
              </div>
            )}
          </main>
        )}
      </div>
      {newProject && (
        <div className="modal-backdrop" onClick={() => setNewProject(false)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-project-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label={t.cancel}
              onClick={() => setNewProject(false)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">ARCAMBE GEOANALYTICS</span>
            <h2 id="new-project-title">{t.newProject}</h2>
            <form onSubmit={(e) => void createProject(e)}>
              <label>
                {t.name}
                <input
                  autoFocus
                  required
                  maxLength={180}
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </label>
              <label>
                {t.description}
                <textarea
                  rows={3}
                  maxLength={2000}
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                />
              </label>
              <div className="modal-actions">
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setNewProject(false)}
                >
                  {t.cancel}
                </button>
                <button className="button primary" disabled={busy}>
                  {t.create}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
