import {
  AlertTriangle,
  BarChart3,
  Bell,
  BellRing,
  BrainCircuit,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock3,
  CloudRain,
  CloudSun,
  Droplets,
  FileText,
  HelpCircle,
  Languages,
  LayoutDashboard,
  Leaf,
  Map as MapIcon,
  MapPin,
  Menu,
  PanelsTopLeft,
  Radar,
  Route,
  Satellite,
  Search,
  Settings,
  ShieldAlert,
  Sprout,
  TrendingUp,
  Wheat,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import ChatWidget from '../components/ChatWidget';
import { HealthGauge } from '../components/dashboard/HealthGauge';
import { KpiCard } from '../components/dashboard/KpiCard';
import {
  getLayerRiskLevel,
  getLayerValue,
  getRiskColor,
  SriLankaProvinceMap,
} from '../components/dashboard/SriLankaProvinceMap';
import type {
  MapLayer,
  RiskLevel,
  ProvinceData,
  ChangeItem,
  PriorityAction,
  AgentActivity,
} from '../data/mockApi';
import { fetchDashboard } from '../services/api';
import type { DashboardPayload } from '../services/api';

const layerLabels: Record<MapLayer, string> = {
  cropHealth: 'Crop Health',
  rainfallRisk: 'Rainfall Risk',
  pestRisk: 'Pest Risk',
};

const layerDescriptions: Record<MapLayer, string> = {
  cropHealth: 'Vegetation health and field-condition score',
  rainfallRisk: 'Excess rain, runoff and flood exposure',
  pestRisk: 'Climate-supported pest and disease pressure',
};

const legendByLayer: Record<MapLayer, { label: string; range: string; level: RiskLevel }[]> = {
  cropHealth: [
    { label: 'Healthy', range: '80–100', level: 'Healthy' },
    { label: 'Watch', range: '60–79', level: 'Watch' },
    { label: 'Stressed', range: '40–59', level: 'Moderate Risk' },
    { label: 'Critical', range: '0–39', level: 'High Risk' },
  ],
  rainfallRisk: [
    { label: 'Low risk', range: '0–25', level: 'Healthy' },
    { label: 'Watch', range: '26–45', level: 'Watch' },
    { label: 'Moderate', range: '46–70', level: 'Moderate Risk' },
    { label: 'High risk', range: '71–100', level: 'High Risk' },
  ],
  pestRisk: [
    { label: 'Low risk', range: '0–25', level: 'Healthy' },
    { label: 'Watch', range: '26–45', level: 'Watch' },
    { label: 'Moderate', range: '46–70', level: 'Moderate Risk' },
    { label: 'High risk', range: '71–100', level: 'High Risk' },
  ],
};

const riskClass = (risk: RiskLevel) => risk.toLowerCase().replaceAll(' ', '-');

export default function OverviewPage() {
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [selectedProvince, setSelectedProvince] = useState('Eastern');
  const [activeLayer, setActiveLayer] = useState<MapLayer>('cropHealth');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [provinceSort, setProvinceSort] = useState<'risk' | 'name'>('risk');

  useEffect(() => {
    let active = true;
    void fetchDashboard().then((payload) => {
      if (active) setDashboard(payload);
    });
    return () => {
      active = false;
    };
  }, []);

  const provinces: Record<string, ProvinceData> = (dashboard?.provinces ?? {}) as Record<
    string,
    ProvinceData
  >;
  const selectedData = provinces[selectedProvince];

  const sortedProvinces = useMemo<ProvinceData[]>(() => {
    const items: ProvinceData[] = Object.values(provinces);

    if (provinceSort === 'name') {
      return [...items].sort((a, b) => a.name.localeCompare(b.name));
    }

    return [...items].sort((a, b) => a.healthScore - b.healthScore);
  }, [provinceSort, provinces]);

  if (!dashboard || !selectedData) {
    return (
      <div className="loading-screen">
        <div className="loading-brand">
          <Leaf size={24} /> Mihimura
        </div>
        <div className="loading-line" />
        <p>Preparing agricultural intelligence…</p>
      </div>
    );
  }

  const layerValue = getLayerValue(selectedProvince, activeLayer, provinces);
  const selectedRisk = getLayerRiskLevel(layerValue, activeLayer);
  const selectedColor = getRiskColor(selectedRisk);
  const generatedDate = new Date(dashboard.generatedAt);
  const updatedLabel = Number.isNaN(generatedDate.getTime())
    ? 'Just now'
    : generatedDate.toLocaleString('en-LK', { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <div className="app-shell">
      <aside className={`sidebar${sidebarOpen ? ' is-open' : ''}`}>
        <div className="brand-block">
          <div className="brand-mark">
            <Leaf size={22} />
          </div>
          <div>
            <strong>Mihimura</strong>
            <span>Agri Intelligence</span>
          </div>
          <button
            className="sidebar-close"
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          <button
            className="nav-link active"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/overview';
            }}
          >
            <LayoutDashboard size={19} />
            <span>Overview</span>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/overview';
            }}
          >
            <MapIcon size={19} />
            <span>Province Map</span>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/climate';
            }}
          >
            <BellRing size={19} />
            <span>Threat Alerts</span>
            <em>{dashboard.summary.criticalThreats}</em>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/farms';
            }}
          >
            <PanelsTopLeft size={19} />
            <span>Fields</span>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/reports';
            }}
          >
            <BarChart3 size={19} />
            <span>Analytics</span>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/reports';
            }}
          >
            <FileText size={19} />
            <span>Reports</span>
          </button>
          <button
            className="nav-link"
            type="button"
            onClick={() => {
              window.location.hash = '#/app/settings';
            }}
          >
            <Settings size={19} />
            <span>Settings</span>
          </button>
        </nav>

        <div className="sidebar-system-card">
          <div className="system-row">
            <span className="system-indicator" />
            <div>
              <small>Data status</small>
              <strong>
                {dashboard._connection === 'backend' ? 'Backend connected' : 'Demo fallback active'}
              </strong>
            </div>
          </div>
          <div className="system-row">
            <Clock3 size={17} />
            <div>
              <small>Last synchronised</small>
              <strong>{updatedLabel}</strong>
            </div>
          </div>
        </div>

        <button className="help-link" type="button">
          <HelpCircle size={17} /> Help and documentation
        </button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="icon-button menu-button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>
            <div>
              <h1>National Intelligence Centre</h1>
              <p>Climate-resilient agriculture monitoring for Sri Lanka</p>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="global-search">
              <Search size={17} />
              <input aria-label="Search fields or provinces" placeholder="Search provinces, fields…" />
            </div>
            <button type="button" className="compact-control">
              <Languages size={17} />
              <span>EN</span>
              <ChevronDown size={14} />
            </button>
            <button type="button" className="icon-button notification-button" aria-label="Notifications">
              <Bell size={19} />
              <span />
            </button>
            <div className="user-chip">
              <div className="avatar">AV</div>
              <div>
                <strong>Agri Officer</strong>
                <span>National view</span>
              </div>
              <ChevronDown size={15} />
            </div>
          </div>
        </header>

        <div className="dashboard-content">
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <MapPin size={14} /> Sri Lanka · All 9 provinces
              </div>
              <h2>Agricultural Situation Overview</h2>
              <p>Detect changes, understand causes and prioritise interventions from one operational view.</p>
            </div>
            <div className="heading-controls">
              <button type="button" className="date-control">
                <Calendar size={17} />
                <span>Last 7 days</span>
                <ChevronDown size={15} />
              </button>
              <button type="button" className="primary-button">
                <FileText size={17} /> Generate situation report
              </button>
            </div>
          </section>

          <section className="kpi-grid" aria-label="National key performance indicators">
            <KpiCard
              label="National crop health"
              value={`${dashboard.summary.cropHealth}%`}
              trend={`↑ ${dashboard.summary.cropHealthChange}%`}
              note="Weighted health score across monitored crop area"
              tone="green"
              icon={Sprout}
              sparkline={[57, 59, 58, 61, 62, 63, 64]}
            />
            <KpiCard
              label="Agricultural area at risk"
              value={`${dashboard.summary.atRiskArea} ac`}
              trend={`+${dashboard.summary.newlyAtRiskArea} ac today`}
              note="Area currently requiring inspection or action"
              tone="orange"
              icon={ShieldAlert}
              sparkline={[72, 78, 83, 91, 96, 109, 124]}
            />
            <KpiCard
              label="Water deficit"
              value={`${dashboard.summary.waterDeficit}%`}
              trend={`${dashboard.summary.irrigationNeed.toLocaleString()} L`}
              note="Estimated irrigation required during the next 48 hours"
              tone="blue"
              icon={Droplets}
              sparkline={[13, 14, 13, 16, 17, 19, 18]}
            />
            <KpiCard
              label="Active climate threats"
              value={`${dashboard.summary.activeThreats}`}
              trend={`${dashboard.summary.criticalThreats} critical`}
              note="Combined drought, rainfall, heat and pest signals"
              tone="red"
              icon={Radar}
              sparkline={[8, 9, 11, 10, 13, 15, 17]}
            />
            <KpiCard
              label="Estimated yield protected"
              value={`${dashboard.summary.yieldProtected} t`}
              trend={`↑ ${dashboard.summary.yieldProtectedChange} t`}
              note="Projected impact of verified interventions"
              tone="purple"
              icon={Wheat}
              sparkline={[7.2, 8.1, 9.4, 10.3, 11.7, 13.1, 14.8]}
            />
          </section>

          <section className="intelligence-grid">
            <article className="card map-card">
              <header className="card-header map-card-header">
                <div>
                  <div className="card-title-row">
                    <MapIcon size={20} />
                    <h3>Agricultural Risk Map</h3>
                    <button className="info-button" type="button" aria-label="Map information">
                      i
                    </button>
                  </div>
                  <p>{layerDescriptions[activeLayer]}</p>
                </div>
                <div className="layer-tabs" role="tablist" aria-label="Map data layers">
                  {(Object.keys(layerLabels) as MapLayer[]).map((layer) => (
                    <button
                      type="button"
                      key={layer}
                      className={activeLayer === layer ? 'active' : ''}
                      onClick={() => setActiveLayer(layer)}
                      role="tab"
                      aria-selected={activeLayer === layer}
                    >
                      {layerLabels[layer]}
                    </button>
                  ))}
                </div>
              </header>

              <div className="map-content">
                <div className="map-summary-overlay">
                  <div className="map-summary-icon">
                    <CloudSun size={21} />
                  </div>
                  <div>
                    <span>National monitoring</span>
                    <strong>9 provinces · 25 districts</strong>
                    <small>Satellite, weather, IoT and farmer reports</small>
                  </div>
                </div>

                <SriLankaProvinceMap
                  selectedProvince={selectedProvince}
                  activeLayer={activeLayer}
                  provinces={provinces}
                  onSelectProvince={setSelectedProvince}
                />

                <div className="map-legend">
                  <strong>{layerLabels[activeLayer]} scale</strong>
                  {legendByLayer[activeLayer].map((item) => (
                    <div className="legend-row" key={item.label}>
                      <span style={{ background: getRiskColor(item.level) }} />
                      <em>{item.label}</em>
                      <small>{item.range}</small>
                    </div>
                  ))}
                </div>
              </div>
            </article>

            <aside className="card province-detail-card">
              <header className="province-detail-header">
                <div>
                  <span className="status-dot" style={{ background: selectedColor }} />
                  <div>
                    <small>Selected province</small>
                    <h3>{selectedProvince} Province</h3>
                  </div>
                </div>
                <span className={`risk-badge ${riskClass(selectedRisk)}`}>{selectedRisk}</span>
              </header>

              <div className="score-section">
                <HealthGauge value={layerValue} color={selectedColor} />
                <div className="score-copy">
                  <span>{layerLabels[activeLayer]} score</span>
                  <strong style={{ color: selectedColor }}>{selectedRisk}</strong>
                  <p className={selectedData.trend >= 0 ? 'positive-text' : 'negative-text'}>
                    {selectedData.trend >= 0 ? '↑' : '↓'} {Math.abs(selectedData.trend)} points{' '}
                    <span>vs last 7 days</span>
                  </p>
                </div>
              </div>

              <div className="province-metrics">
                <div className="metric-box">
                  <AlertTriangle size={18} />
                  <span>Active alerts</span>
                  <strong>{selectedData.activeAlerts}</strong>
                </div>
                <div className="metric-box">
                  <CloudRain size={18} />
                  <span>Rainfall · 7d</span>
                  <strong>{selectedData.rainfall7d} mm</strong>
                  <small>{selectedData.rainfallAvgDiff}% vs average</small>
                </div>
                <div className="metric-box">
                  <Leaf size={18} />
                  <span>Crop coverage</span>
                  <strong>{selectedData.cropCoverage}%</strong>
                  <small>of arable land</small>
                </div>
                <div className="metric-box">
                  <Sprout size={18} />
                  <span>Top crop</span>
                  <strong>{selectedData.topCrop}</strong>
                </div>
              </div>

              <div className="moisture-panel">
                <div className="moisture-heading">
                  <div>
                    <Droplets size={17} />
                    <span>Soil moisture</span>
                  </div>
                  <strong>{selectedData.soilMoisture}%</strong>
                </div>
                <div className="moisture-scale">
                  <span className="moisture-current" style={{ left: `${selectedData.soilMoisture}%` }} />
                  <span className="moisture-optimal" />
                </div>
                <div className="moisture-labels">
                  <span>Dry</span>
                  <span>Optimal 31–38%</span>
                  <span>Excess</span>
                </div>
              </div>

              <div className="next-action-box">
                <div>
                  <Route size={18} />
                  <span>Recommended next action</span>
                </div>
                <strong>{selectedData.nextAction}</strong>
                <button type="button">
                  Open intervention plan <ChevronRight size={16} />
                </button>
              </div>
            </aside>
          </section>

          <section className="decision-grid">
            <article className="card changes-card">
              <header className="card-header">
                <div>
                  <div className="card-title-row">
                    <TrendingUp size={20} />
                    <h3>What changed since yesterday?</h3>
                  </div>
                  <p>Changes that may alter today’s field priorities</p>
                </div>
                <button className="text-button" type="button">
                  View timeline <ChevronRight size={15} />
                </button>
              </header>
              <div className="changes-list">
                {dashboard.changes.map((change: ChangeItem) => (
                  <button
                    type="button"
                    className="change-item"
                    key={change.id}
                    onClick={() => change.province !== 'National' && setSelectedProvince(change.province)}
                  >
                    <span className={`change-icon ${change.tone}`}>
                      <TrendingUp size={17} />
                    </span>
                    <div>
                      <strong>{change.title}</strong>
                      <p>{change.detail}</p>
                    </div>
                    <em>{change.province}</em>
                  </button>
                ))}
              </div>
            </article>

            <article className="card actions-card">
              <header className="card-header">
                <div>
                  <div className="card-title-row">
                    <ShieldAlert size={20} />
                    <h3>Priority Actions</h3>
                  </div>
                  <p>Ranked by urgency, impact and AI confidence</p>
                </div>
                <button className="text-button" type="button">
                  All actions <ChevronRight size={15} />
                </button>
              </header>
              <div className="priority-list">
                {dashboard.priorityActions.slice(0, 3).map((action: PriorityAction) => (
                  <div className="priority-item" key={action.id}>
                    <div className="priority-topline">
                      <span className={`severity-chip ${action.severity.toLowerCase()}`}>
                        {action.severity}
                      </span>
                      <span>{action.province}</span>
                      <time>
                        <Clock3 size={13} /> {action.deadline}
                      </time>
                    </div>
                    <h4>{action.title}</h4>
                    <p>{action.description}</p>
                    <div className="evidence-line">
                      <BrainCircuit size={15} />
                      <span>{action.evidence}</span>
                    </div>
                    <div className="priority-footer">
                      <strong>{action.impact}</strong>
                      <button type="button">
                        {action.buttonText} <ChevronRight size={15} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <section className="analytics-grid">
            <article className="card province-table-card">
              <header className="card-header">
                <div>
                  <div className="card-title-row">
                    <BarChart3 size={20} />
                    <h3>Province Performance</h3>
                  </div>
                  <p>Health, threat level and operational next step</p>
                </div>
                <button
                  className="sort-button"
                  type="button"
                  onClick={() => setProvinceSort((current) => (current === 'risk' ? 'name' : 'risk'))}
                >
                  Sort by {provinceSort === 'risk' ? 'risk' : 'name'} <ChevronDown size={14} />
                </button>
              </header>
              <div className="table-scroll">
                <table className="province-table">
                  <thead>
                    <tr>
                      <th>Province</th>
                      <th>Crop health</th>
                      <th>Rain risk</th>
                      <th>Pest risk</th>
                      <th>Area at risk</th>
                      <th>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedProvinces.map((province) => {
                      const risk = getLayerRiskLevel(province.healthScore, 'cropHealth');
                      return (
                        <tr
                          key={province.id}
                          className={province.name === selectedProvince ? 'selected' : ''}
                          onClick={() => setSelectedProvince(province.name)}
                        >
                          <td>
                            <span className="table-province-dot" style={{ background: getRiskColor(risk) }} />
                            <strong>{province.name}</strong>
                            <small>{province.topCrop}</small>
                          </td>
                          <td>
                            <div className="score-cell">
                              <span>{province.healthScore}</span>
                              <div>
                                <i
                                  style={{
                                    width: `${province.healthScore}%`,
                                    background: getRiskColor(risk),
                                  }}
                                />
                              </div>
                            </div>
                          </td>
                          <td>
                            <span
                              className={`mini-score ${riskClass(getLayerRiskLevel(province.rainfallRisk, 'rainfallRisk'))}`}
                            >
                              {province.rainfallRisk}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`mini-score ${riskClass(getLayerRiskLevel(province.pestRisk, 'pestRisk'))}`}
                            >
                              {province.pestRisk}
                            </span>
                          </td>
                          <td>{province.atRiskArea} ac</td>
                          <td className={province.trend >= 0 ? 'positive-text' : 'negative-text'}>
                            {province.trend >= 0 ? '↑' : '↓'} {Math.abs(province.trend)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="card agent-card">
              <header className="card-header">
                <div>
                  <div className="card-title-row">
                    <BrainCircuit size={20} />
                    <h3>Multi-Agent Operations</h3>
                  </div>
                  <p>How the intelligence pipeline reached its recommendations</p>
                </div>
                <span className="live-pill">
                  <i /> Live
                </span>
              </header>
              <div className="agent-flow">
                {dashboard.agentActivity.map((item: AgentActivity, index: number) => {
                  const AgentIcon =
                    index === 0 ? Satellite : index === 1 ? CloudSun : index === 2 ? Search : Route;
                  return (
                    <div className="agent-event" key={item.id}>
                      <div className={`agent-icon ${item.status}`}>
                        <AgentIcon size={18} />
                      </div>
                      <div>
                        <div>
                          <strong>{item.agent}</strong>
                          <time>{item.time}</time>
                        </div>
                        <p>{item.action}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="agent-reasoning">
                <strong>Latest reasoning chain</strong>
                <div>
                  <span>Satellite stress</span>
                  <ChevronRight size={14} />
                  <span>Climate verified</span>
                  <ChevronRight size={14} />
                  <span>Action generated</span>
                </div>
              </div>
            </article>
          </section>

          <footer className="dashboard-footer">
            <Leaf size={16} /> Empowering climate-resilient agriculture with explainable intelligence
          </footer>
        </div>
      </main>

      <ChatWidget province={selectedProvince} />
    </div>
  );
}
