import { useEffect, useState, type ReactNode } from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import BootSplash from './components/BootSplash';
import PublicLayout from './components/layout/PublicLayout';
import AppShell from './components/layout/AppShell';
import AuthExperience from './components/auth/AuthExperience';
import OnboardingJourney from './components/auth/OnboardingJourney';
import { AboutPage, HelpPage, HowItWorksPage, ImpactPage, PartnersPage, WelcomePage } from './pages/public';
import DashboardPage from './pages/DashboardPage';
import OverviewPage from './pages/OverviewPage';
import {
  ClimateRiskPage,
  CommunityPage,
  DisasterMapPage,
  LocalSituationPage,
  SatellitePage,
} from './pages/intelligence';
import { AIPage, ExpertEscalationPage, RecommendationHistoryPage, ScanPage } from './pages/ai';
import {
  DiaryPage,
  ExpensesPage,
  FarmMapPage,
  FarmsPage,
  HarvestPage,
  ProjectDetailPage,
  ProjectsPage,
  TasksPage,
} from './pages/farm';
import {
  CartPage,
  ComparePage,
  CooperativePage,
  MarketplacePage,
  OrdersPage,
  SuppliersPage,
} from './pages/commerce';
import { AdminPage, AgronomistPage, GovernmentPage, ReportsPage, SettingsPage } from './pages/account';
import './index.css';

function Protected({ children }: { children: ReactNode }) {
  const { user, profile, loading } = useAuth();
  if (loading) return <BootSplash />;
  if (!user || !profile) return <Navigate to="/auth" replace />;
  if (!profile?.onboarding_complete) return <Navigate to="/onboarding" replace />;
  return children;
}
function RoleGate({
  children,
  roles,
  managerAllowed = false,
}: {
  children: ReactNode;
  roles: string[];
  managerAllowed?: boolean;
}) {
  const { profile } = useAuth();
  const role = profile?.role || 'farmer';
  const verified = Boolean(profile?.professional_verified);
  const allowed = (managerAllowed && role === 'manager') || (verified && roles.includes(role));
  if (allowed) return children;
  return (
    <section className="access-gate">
      <div className="access-gate-mark">✓</div>
      <span>Professional workspace</span>
      <h2>Verification is required before this workspace is unlocked.</h2>
      <p>
        Your farmer-facing tools remain available now. Agronomist, supplier, analyst and administration
        workspaces require organization verification so that regional data, expert cases and operational
        controls cannot be accessed through self-declared roles.
      </p>
      <div>
        <a href="#/app/dashboard">Return to dashboard</a>
        <a href="#/app/settings">Review profile</a>
      </div>
    </section>
  );
}
function OnboardingGate() {
  const { user, profile, loading } = useAuth();
  if (loading) return <BootSplash />;
  if (!user || !profile) return <Navigate to="/auth" replace />;
  if (profile?.onboarding_complete) return <Navigate to="/app/dashboard" replace />;
  return <OnboardingJourney />;
}
function SplashGate({ children }: { children: ReactNode }) {
  const [show, setShow] = useState(() => sessionStorage.getItem('mihimura_boot_seen') !== '1');
  useEffect(() => {
    if (!show) return;
    const t = setTimeout(() => {
      sessionStorage.setItem('mihimura_boot_seen', '1');
      setShow(false);
    }, 1800);
    return () => clearTimeout(t);
  }, [show]);
  return show ? <BootSplash /> : children;
}

export default function App() {
  return (
    <AuthProvider>
      <LanguageProvider>
        <HashRouter>
          <SplashGate>
            <Routes>
              <Route element={<PublicLayout />}>
                <Route path="/welcome" element={<WelcomePage />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="/how-it-works" element={<HowItWorksPage />} />
                <Route path="/impact" element={<ImpactPage />} />
                <Route path="/partners" element={<PartnersPage />} />
                <Route path="/help" element={<HelpPage />} />
              </Route>
              <Route path="/auth" element={<AuthExperience />} />
              <Route path="/onboarding" element={<OnboardingGate />} />
              <Route
                path="/app/overview"
                element={
                  <Protected>
                    <OverviewPage />
                  </Protected>
                }
              />
              <Route
                path="/app"
                element={
                  <Protected>
                    <AppShell />
                  </Protected>
                }
              >
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="local" element={<LocalSituationPage />} />
                <Route path="climate" element={<ClimateRiskPage />} />
                <Route path="disaster-map" element={<DisasterMapPage />} />
                <Route path="satellite" element={<SatellitePage />} />
                <Route path="community" element={<CommunityPage />} />
                <Route path="ai" element={<AIPage />} />
                <Route path="scan" element={<ScanPage />} />
                <Route path="recommendations" element={<RecommendationHistoryPage />} />
                <Route path="expert" element={<ExpertEscalationPage />} />
                <Route path="farms" element={<FarmsPage />} />
                <Route path="farm-map" element={<FarmMapPage />} />
                <Route path="projects" element={<ProjectsPage />} />
                <Route path="projects/:projectId" element={<ProjectDetailPage />} />
                <Route path="tasks" element={<TasksPage />} />
                <Route path="diary" element={<DiaryPage />} />
                <Route path="expenses" element={<ExpensesPage />} />
                <Route path="harvest" element={<HarvestPage />} />
                <Route path="marketplace" element={<MarketplacePage />} />
                <Route path="suppliers" element={<SuppliersPage />} />
                <Route path="compare" element={<ComparePage />} />
                <Route path="cart" element={<CartPage />} />
                <Route path="orders" element={<OrdersPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route
                  path="agronomist"
                  element={
                    <RoleGate roles={['agronomist', 'expert', 'admin']}>
                      <AgronomistPage />
                    </RoleGate>
                  }
                />
                <Route
                  path="cooperative"
                  element={
                    <RoleGate roles={['supplier', 'admin']} managerAllowed>
                      <CooperativePage />
                    </RoleGate>
                  }
                />
                <Route
                  path="government"
                  element={
                    <RoleGate roles={['analyst', 'admin']}>
                      <GovernmentPage />
                    </RoleGate>
                  }
                />
                <Route
                  path="admin"
                  element={
                    <RoleGate roles={['admin']}>
                      <AdminPage />
                    </RoleGate>
                  }
                />
              </Route>
              <Route path="/" element={<Navigate to="/welcome" replace />} />
              <Route path="*" element={<Navigate to="/welcome" replace />} />
            </Routes>
          </SplashGate>
        </HashRouter>
      </LanguageProvider>
    </AuthProvider>
  );
}
