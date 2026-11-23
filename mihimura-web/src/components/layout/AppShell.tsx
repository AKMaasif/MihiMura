import {
  Activity,
  Bell,
  Bot,
  Camera,
  ChevronDown,
  CircleDollarSign,
  ClipboardList,
  CloudSun,
  Database,
  FileBarChart,
  Gauge,
  Globe2,
  Handshake,
  Languages,
  Leaf,
  LogOut,
  Map,
  MapPinned,
  Menu,
  PackageSearch,
  Radar,
  ReceiptText,
  Search,
  Settings,
  ShoppingCart,
  Sprout,
  Stethoscope,
  Store,
  Users,
  Wheat,
  X,
  Check,
  Clock3,
  ArrowRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLanguage, type AppLanguage } from '../../context/LanguageContext';
import { platformApi } from '../../services/platformApi';

type NavItem = readonly [path: string, labelKey: string, Icon: LucideIcon];

type NavGroup = {
  labelKey: string;
  items: readonly NavItem[];
};

const groups: readonly NavGroup[] = [
  {
    labelKey: 'today',
    items: [
      ['/app/dashboard', 'dashboard', Gauge],
      ['/app/overview', 'nationalIntelligence', Globe2],
      ['/app/local', 'localSituation', MapPinned],
    ],
  },

  {
    labelKey: 'intelligence',
    items: [
      ['/app/climate', 'riskDisaster', Radar],
      ['/app/disaster-map', 'disasterMap', Map],
      ['/app/satellite', 'satelliteView', CloudSun],
      ['/app/community', 'communitySentinel', Users],
    ],
  },

  {
    labelKey: 'aiSupport',
    items: [
      ['/app/ai', 'mihiMuraAI', Bot],
      ['/app/scan', 'cropHealthScan', Camera],
      ['/app/recommendations', 'recommendationHistory', ClipboardList],
      ['/app/expert', 'expertEscalation', Stethoscope],
    ],
  },

  {
    labelKey: 'farmManagement',
    items: [
      ['/app/farms', 'myFarms', Sprout],
      ['/app/farm-map', 'farmMap', Map],
      ['/app/projects', 'projects', Wheat],
      ['/app/tasks', 'tasks', ClipboardList],
      ['/app/diary', 'fieldDiary', ReceiptText],
      ['/app/expenses', 'expenses', CircleDollarSign],
      ['/app/harvest', 'harvest', Activity],
    ],
  },

  {
    labelKey: 'commerce',
    items: [
      ['/app/marketplace', 'verifiedProducts', Store],
      ['/app/suppliers', 'suppliers', Handshake],
      ['/app/compare', 'compare', PackageSearch],
      ['/app/cart', 'cart', ShoppingCart],
      ['/app/orders', 'ordersTracking', ReceiptText],
    ],
  },

  {
    labelKey: 'insights',
    items: [
      ['/app/reports', 'reportsImpact', FileBarChart],
      ['/app/settings', 'settingsPrivacy', Settings],
    ],
  },

  {
    labelKey: 'professional',
    items: [
      ['/app/agronomist', 'agronomistConsole', Stethoscope],
      ['/app/cooperative', 'cooperativePortal', Handshake],
      ['/app/government', 'govAnalytics', FileBarChart],
      ['/app/admin', 'administration', Database],
    ],
  },
];

const titleKeys: Record<string, string> = {
  dashboard: 'title_dashboard',
  overview: 'title_overview',
  local: 'title_local',
  climate: 'title_climate',
  'disaster-map': 'title_disasterMap',
  satellite: 'title_satellite',
  community: 'title_community',
  ai: 'title_ai',
  scan: 'title_scan',
  recommendations: 'title_recommendations',
  expert: 'title_expert',
  farms: 'title_farms',
  'farm-map': 'title_farmMap',
  projects: 'title_projects',
  tasks: 'title_tasks',
  diary: 'title_diary',
  expenses: 'title_expenses',
  harvest: 'title_harvest',
  marketplace: 'title_marketplace',
  suppliers: 'title_suppliers',
  compare: 'title_compare',
  cart: 'title_cart',
  orders: 'title_orders',
  reports: 'title_reports',
  settings: 'title_settings',
  agronomist: 'title_agronomist',
  cooperative: 'title_cooperative',
  government: 'title_government',
  admin: 'title_admin',
};

type SearchResult = {
  id: string;
  kind: 'page' | 'farm' | 'project' | 'task';
  title: string;
  subtitle: string;
  path: string;
  Icon: LucideIcon;
};

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [searchData, setSearchData] = useState<{ farms: any[]; projects: any[]; tasks: any[] }>({
    farms: [],
    projects: [],
    tasks: [],
  });
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const searchWrap = useRef<HTMLDivElement>(null);
  const languageWrap = useRef<HTMLDivElement>(null);
  const notificationWrap = useRef<HTMLDivElement>(null);
  const { profile, user, logout } = useAuth();
  const { language, setLanguage, t, shortCode, changing, locale } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const key = location.pathname.split('/').filter(Boolean).pop() || 'dashboard';
  const role = profile?.role || 'farmer';
  const verified = Boolean(profile?.professional_verified);

  const can = (path: string) =>
    user?.provider === 'demo' ||
    !path.startsWith('/app/') ||
    !['/app/agronomist', '/app/cooperative', '/app/government', '/app/admin'].includes(path) ||
    (path === '/app/agronomist' && verified && ['agronomist', 'expert', 'admin'].includes(role)) ||
    (path === '/app/cooperative' &&
      (role === 'manager' || (verified && ['supplier', 'admin'].includes(role)))) ||
    (path === '/app/government' && verified && ['analyst', 'admin'].includes(role)) ||
    (path === '/app/admin' && verified && role === 'admin');

  const loadSearchData = async () => {
    const r = await Promise.allSettled([platformApi.farms(), platformApi.projects(), platformApi.tasks()]);
    setSearchData({
      farms: r[0].status === 'fulfilled' ? r[0].value : [],
      projects: r[1].status === 'fulfilled' ? r[1].value : [],
      tasks: r[2].status === 'fulfilled' ? r[2].value : [],
    });
  };

  const loadNotifications = async () => {
    setLoadingNotifications(true);
    try {
      setNotifications(await platformApi.notifications());
    } catch {
      setNotifications([]);
    } finally {
      setLoadingNotifications(false);
    }
  };

  useEffect(() => {
    void loadSearchData();
    void loadNotifications();
    const id = window.setInterval(() => void loadNotifications(), 60000);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    void loadSearchData();
  }, [location.pathname]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      const target = e.target as Node;
      if (searchWrap.current && !searchWrap.current.contains(target)) setSearchOpen(false);
      if (languageWrap.current && !languageWrap.current.contains(target)) setLanguageOpen(false);
      if (notificationWrap.current && !notificationWrap.current.contains(target)) setNotificationOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const pageResults = useMemo<SearchResult[]>(() => {
    return groups.flatMap((group) =>
      group.items
        .filter(([path]) => can(path))
        .map(
          ([path, labelKey, Icon]): SearchResult => ({
            id: `page:${path}`,
            kind: 'page',
            title: t(labelKey),
            subtitle: t('pages'),
            path,
            Icon,
          }),
        ),
    );
  }, [language, role, verified, user?.provider]);

  const searchResults = useMemo<SearchResult[]>(() => {
    const q = searchQuery.trim().toLocaleLowerCase(locale);
    if (!q) return pageResults.slice(0, 6);
    const has = (...parts: any[]) => parts.filter(Boolean).join(' ').toLocaleLowerCase(locale).includes(q);
    const pages = pageResults.filter((x) => has(x.title, x.subtitle, x.path));
    const farms = searchData.farms
      .filter((x) => has(x.name, x.crop, x.district, x.province))
      .map((x) => ({
        id: `farm:${x.id}`,
        kind: 'farm' as const,
        title: x.name || 'Farm',
        subtitle: [x.crop, x.district].filter(Boolean).join(' · ') || t('farms'),
        path: '/app/farms',
        Icon: Sprout,
      }));
    const projects = searchData.projects
      .filter((x) => has(x.crop, x.variety, x.stage, x.farm_name, x.season))
      .map((x) => ({
        id: `project:${x.id}`,
        kind: 'project' as const,
        title: `${x.crop || 'Crop'} · ${x.stage || ''}`,
        subtitle: x.farm_name || t('cropProjects'),
        path: `/app/projects/${x.id}`,
        Icon: Wheat,
      }));
    const tasks = searchData.tasks
      .filter((x) => has(x.title, x.task_type, x.crop, x.farm_name, x.instructions))
      .map((x) => ({
        id: `task:${x.id}`,
        kind: 'task' as const,
        title: x.title || 'Task',
        subtitle: [x.farm_name, x.crop].filter(Boolean).join(' · ') || t('taskResults'),
        path: '/app/tasks',
        Icon: ClipboardList,
      }));
    return [...pages, ...farms, ...projects, ...tasks].slice(0, 9);
  }, [searchQuery, pageResults, searchData, locale, language]);

  const chooseSearch = (result: SearchResult) => {
    navigate(result.path);
    setSearchQuery('');
    setSearchOpen(false);
  };
  const unread = notifications.filter((n) => !Boolean(n.acknowledged));
  const acknowledge = async (n: any) => {
    try {
      if (!n.acknowledged) await platformApi.ackNotification(n.id);
      setNotifications((items) => items.map((x) => (x.id === n.id ? { ...x, acknowledged: 1 } : x)));
    } catch {}
    const hay = `${n.title || ''} ${n.body || ''}`.toLowerCase();
    navigate(
      hay.includes('risk') || hay.includes('rain') || hay.includes('flood') ? '/app/climate' : '/app/tasks',
    );
    setNotificationOpen(false);
  };
  const markAll = async () => {
    const ids = unread.map((n) => n.id);
    setNotifications((items) => items.map((x) => (ids.includes(x.id) ? { ...x, acknowledged: 1 } : x)));
    await Promise.allSettled(ids.map((id) => platformApi.ackNotification(id)));
  };

  const selectLanguage = async (next: AppLanguage) => {
    setLanguageOpen(false);
    await setLanguage(next);
  };

  return (
    <div className="app-workspace">
      <aside className={`app-sidebar ${open ? 'open' : ''}`}>
        <div className="side-brand">
          <span>
            <Leaf />
          </span>
          <div>
            <b>MihiMura</b>
            <small>Field Intelligence</small>
          </div>
          <button onClick={() => setOpen(false)} aria-label="Close navigation">
            <X />
          </button>
        </div>
        <div className="side-context">
          <small>{t('activeRegion')}</small>
          <b>
            {profile?.district || 'Ampara'}, {t('sriLanka')}
          </b>
          <span>
            <i /> {t('liveDecisionSupport')}
          </span>
        </div>
        <nav>
          {groups.map((g) => (
            <div className="nav-group" key={g.labelKey}>
              <small>{t(g.labelKey)}</small>
              {g.items
                .filter(([path]) => can(path))
                .map(([path, labelKey, Icon]) => (
                  <NavLink
                    key={path}
                    to={path}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) => (isActive ? 'active' : '')}
                  >
                    <Icon size={17} />
                    <span>{t(labelKey)}</span>
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>
        <div className="side-footer">
          <button onClick={() => navigate('/app/settings')}>
            <Settings />
            {t('preferences')}
          </button>
          <button
            onClick={async () => {
              try {
                await logout();
                navigate('/welcome');
              } catch (error) {
                window.alert(error instanceof Error ? error.message : 'Sign-out failed. Try again.');
              }
            }}
          >
            <LogOut />
            {t('signOut')}
          </button>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div className="top-title">
            <button className="mobile-nav" onClick={() => setOpen(true)}>
              <Menu />
            </button>
            <div>
              <span>MihiMura · {t('sriLanka')}</span>
              <h1>{t(titleKeys[key] || 'mihiMuraAI')}</h1>
            </div>
          </div>
          <div className="top-actions">
            <div className="top-search-wrap" ref={searchWrap}>
              <label className={`top-search ${searchOpen ? 'active' : ''}`}>
                <Search />
                <input
                  value={searchQuery}
                  onFocus={() => setSearchOpen(true)}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSearchOpen(true);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && searchResults[0]) chooseSearch(searchResults[0]);
                    if (e.key === 'Escape') setSearchOpen(false);
                  }}
                  placeholder={t('searchPlaceholder')}
                  aria-label={t('search')}
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="search-clear"
                    onClick={() => setSearchQuery('')}
                    aria-label="Clear search"
                  >
                    <X />
                  </button>
                )}
              </label>
              {searchOpen && (
                <div className="top-popover search-popover">
                  {searchResults.length ? (
                    searchResults.map((r) => (
                      <button key={r.id} className="search-result" onClick={() => chooseSearch(r)}>
                        <span className={`search-kind ${r.kind}`}>
                          <r.Icon />
                        </span>
                        <div>
                          <b>{r.title}</b>
                          <small>{r.subtitle}</small>
                        </div>
                        <ArrowRight />
                      </button>
                    ))
                  ) : (
                    <div className="popover-empty">
                      <Search />
                      <span>{t('noSearchResults')}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="top-menu-wrap" ref={languageWrap}>
              <button
                className={`top-language ${languageOpen ? 'active' : ''}`}
                onClick={() => setLanguageOpen((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={languageOpen}
              >
                <Languages />
                <span>{changing ? t('savingLanguage') : shortCode}</span>
                <ChevronDown className={languageOpen ? 'rotated' : ''} />
              </button>
              {languageOpen && (
                <div className="top-popover language-popover">
                  <div className="popover-title">
                    <Languages />
                    <span>{t('language')}</span>
                  </div>
                  {(['English', 'Sinhala', 'Tamil'] as AppLanguage[]).map((item) => (
                    <button
                      key={item}
                      className={language === item ? 'selected' : ''}
                      onClick={() => void selectLanguage(item)}
                    >
                      <span className="language-symbol">
                        {item === 'English' ? 'EN' : item === 'Sinhala' ? 'සිං' : 'த'}
                      </span>
                      <div>
                        <b>
                          {item === 'English' ? t('english') : item === 'Sinhala' ? t('sinhala') : t('tamil')}
                        </b>
                        <small>{item}</small>
                      </div>
                      {language === item && <Check />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="top-menu-wrap" ref={notificationWrap}>
              <button
                className={`bell ${notificationOpen ? 'active' : ''}`}
                onClick={() => {
                  setNotificationOpen((v) => !v);
                  if (!notificationOpen) void loadNotifications();
                }}
                aria-label={t('notifications')}
                aria-haspopup="menu"
                aria-expanded={notificationOpen}
              >
                <Bell />
                {unread.length > 0 && (
                  <span className="notification-count">{unread.length > 9 ? '9+' : unread.length}</span>
                )}
              </button>
              {notificationOpen && (
                <div className="top-popover notification-popover">
                  <div className="notification-head">
                    <div>
                      <b>{t('notifications')}</b>
                      <small>{unread.length ? `${unread.length} unread` : t('allCaughtUp')}</small>
                    </div>
                    {unread.length > 0 && <button onClick={() => void markAll()}>{t('markAllRead')}</button>}
                  </div>
                  <div className="notification-list">
                    {loadingNotifications && !notifications.length ? (
                      <div className="popover-loading">
                        <i />
                        <span>Loading…</span>
                      </div>
                    ) : notifications.length ? (
                      notifications.slice(0, 7).map((n) => (
                        <button
                          key={n.id}
                          className={`notification-item ${n.acknowledged ? 'read' : 'unread'}`}
                          onClick={() => void acknowledge(n)}
                        >
                          <span className="notification-icon">
                            <Bell />
                          </span>
                          <div>
                            <b>{n.title}</b>
                            <p>{n.body}</p>
                            <small>
                              <Clock3 />
                              {new Date(n.scheduled_at || n.created_at).toLocaleString(locale)}
                            </small>
                          </div>
                          {!n.acknowledged && <i />}
                        </button>
                      ))
                    ) : (
                      <div className="popover-empty">
                        <Bell />
                        <span>{t('noNotifications')}</span>
                      </div>
                    )}
                  </div>
                  <button
                    className="notification-footer"
                    onClick={() => {
                      navigate('/app/tasks');
                      setNotificationOpen(false);
                    }}
                  >
                    {t('openTasks')}
                    <ArrowRight />
                  </button>
                </div>
              )}
            </div>

            <button className="profile-chip" onClick={() => navigate('/app/settings')}>
              <span>
                {(profile?.name || user?.displayName || 'Farmer')
                  .split(' ')
                  .map((x: string) => x[0])
                  .slice(0, 2)
                  .join('')}
              </span>
              <div>
                <b>{profile?.name || user?.displayName || 'Farmer'}</b>
                <small>{profile?.role || t('farmer')}</small>
              </div>
            </button>
          </div>
        </header>
        <div className="app-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
