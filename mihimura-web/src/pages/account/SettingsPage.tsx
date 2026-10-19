import { useState } from 'react';
import { BellRing, Download, Lock, ShieldCheck, Trash2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button, Card, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { enablePushNotifications } from '../../services/push';
import { download } from './download';

export function SettingsPage() {
  const { profile, completeOnboarding, logout } = useAuth();
  const [notice, setNotice] = useState('');
  const [state, setState] = useState<any>({
    language: profile?.language || 'English',
    guidance_mode: profile?.guidance_mode || 'Voice + visual cards',
    location_consent: Boolean(profile?.location_consent),
    notification_channels: profile?.notification_channels || 'Push + SMS fallback',
    accessibility: profile?.accessibility_json
      ? typeof profile.accessibility_json === 'string'
        ? (() => {
            try {
              return JSON.parse(profile.accessibility_json);
            } catch {
              return {};
            }
          })()
        : profile.accessibility_json
      : { largeText: false, highContrast: false, audioNumbers: true },
    community: true,
    mobileData: false,
  });
  const save = async () => {
    await completeOnboarding({
      ...profile,
      ...state,
      accessibility_json: state.accessibility,
      onboarding_complete: true,
    });
    document.documentElement.classList.toggle('large-text', Boolean(state.accessibility.largeText));
    document.documentElement.classList.toggle('high-contrast', Boolean(state.accessibility.highContrast));
    setNotice('Preferences saved and accessibility settings applied to this device.');
  };
  const exportData = async () => {
    const data = {
      profile,
      farms: await platformApi.farms(),
      projects: await platformApi.projects(),
      tasks: await platformApi.tasks(),
      observations: await platformApi.observations(),
      orders: await platformApi.orders(),
      audit: await platformApi.audit(),
    };
    download('mihimura-my-data.json', JSON.stringify(data, null, 2), 'application/json');
  };
  const notify = async () => {
    try {
      const r = await enablePushNotifications();
      if (r.enabled) {
        new Notification('MihiMura notifications enabled', {
          body: 'Browser notifications are enabled for this device.',
        });
        setNotice('Browser notifications enabled. Scheduled notification records are stored in Supabase.');
      } else setNotice(r.reason);
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const requestDelete = async () => {
    if (
      !window.confirm(
        'Request deletion of your MihiMura application profile? This will sign you out and should be followed by identity-provider deletion in production.',
      )
    )
      return;
    await platformApi.requestAccountDeletion();
    setNotice('Deletion request recorded. You are being signed out.');
    setTimeout(() => void logout(), 700);
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <ShieldCheck /> Farmer-controlled account
          </span>
          <h2>Profile, privacy, accessibility & security</h2>
          <p>
            Consent is requested at the moment it is needed, and farmers retain control over sharing, export
            and deletion.
          </p>
        </div>
        <Button onClick={() => void save()}>Save changes</Button>
      </section>
      {notice && (
        <Notice tone="info" title="Account settings">
          {notice}
        </Notice>
      )}
      <div className="settings-grid">
        <Card title="Language & guidance">
          <label>
            Preferred language
            <select value={state.language} onChange={(e) => setState({ ...state, language: e.target.value })}>
              <option>English</option>
              <option>Sinhala</option>
              <option>Tamil</option>
            </select>
          </label>
          <label>
            Guidance style
            <select
              value={state.guidance_mode}
              onChange={(e) => setState({ ...state, guidance_mode: e.target.value })}
            >
              <option>Voice + visual cards</option>
              <option>Text first</option>
              <option>Illustrated steps</option>
              <option>Large text + voice</option>
            </select>
          </label>
          <div className="switch-list">
            <label>
              <span>
                <b>Large interface text</b>
                <small>Improve readability and touch targets.</small>
              </span>
              <input
                type="checkbox"
                checked={Boolean(state.accessibility.largeText)}
                onChange={(e) =>
                  setState({
                    ...state,
                    accessibility: { ...state.accessibility, largeText: e.target.checked },
                  })
                }
              />
            </label>
            <label>
              <span>
                <b>High contrast</b>
                <small>Increase status and surface separation.</small>
              </span>
              <input
                type="checkbox"
                checked={Boolean(state.accessibility.highContrast)}
                onChange={(e) =>
                  setState({
                    ...state,
                    accessibility: { ...state.accessibility, highContrast: e.target.checked },
                  })
                }
              />
            </label>
            <label>
              <span>
                <b>Read critical numbers aloud</b>
                <small>Repeat dates, quantities and warnings.</small>
              </span>
              <input
                type="checkbox"
                checked={Boolean(state.accessibility.audioNumbers)}
                onChange={(e) =>
                  setState({
                    ...state,
                    accessibility: { ...state.accessibility, audioNumbers: e.target.checked },
                  })
                }
              />
            </label>
          </div>
        </Card>
        <Card title="Location & data consent">
          <div className="switch-list">
            <label>
              <span>
                <b>Location-aware guidance</b>
                <small>GPS improves local context; manual district fallback remains available.</small>
              </span>
              <input
                type="checkbox"
                checked={state.location_consent}
                onChange={(e) => setState({ ...state, location_consent: e.target.checked })}
              />
            </label>
            <label>
              <span>
                <b>Anonymous Community Sentinel contribution</b>
                <small>Only aggregated above privacy thresholds.</small>
              </span>
              <input
                type="checkbox"
                checked={state.community}
                onChange={(e) => setState({ ...state, community: e.target.checked })}
              />
            </label>
            <label>
              <span>
                <b>Background refresh on mobile data</b>
                <small>Disable to reduce bandwidth use.</small>
              </span>
              <input
                type="checkbox"
                checked={state.mobileData}
                onChange={(e) => setState({ ...state, mobileData: e.target.checked })}
              />
            </label>
          </div>
          <Notice tone="info" title="Farm data ownership">
            Partner use requires separate consent. Regional analytics should suppress small cells and remove
            exact farm boundaries.
          </Notice>
        </Card>
        <Card title="Notifications">
          <label>
            Preferred channels
            <select
              value={state.notification_channels}
              onChange={(e) => setState({ ...state, notification_channels: e.target.value })}
            >
              <option>Push + SMS fallback</option>
              <option>Push only</option>
              <option>SMS only</option>
              <option>Quiet mode</option>
            </select>
          </label>
          <Button variant="secondary" onClick={() => void notify()}>
            <BellRing /> Enable browser notifications
          </Button>
          <div className="settings-note">
            <b>Production push</b>
            <p>
              MihiMura currently persists scheduled notifications in Supabase and supports browser
              notifications while the app is open. A standards-based background Web Push transport can be
              added later without changing authentication.
            </p>
          </div>
        </Card>
        <Card title="Security & data rights">
          <div className="security-list">
            <div>
              <Lock />
              <span>
                <b>Authentication</b>
                <small>Supabase Auth email/password + Google when configured</small>
              </span>
              <Status tone="green">Protected</Status>
            </div>
            <div>
              <ShieldCheck />
              <span>
                <b>Consequential actions</b>
                <small>Confirmation gates + audit events</small>
              </span>
              <Status tone="green">Enabled</Status>
            </div>
          </div>
          <div className="stack-actions">
            <Button variant="secondary" onClick={() => void exportData()}>
              <Download /> Download my data
            </Button>
            <Button variant="secondary" onClick={() => void logout()}>
              Sign out all current browser access
            </Button>
            <Button variant="danger" onClick={() => void requestDelete()}>
              <Trash2 /> Request account deletion
            </Button>
          </div>
        </Card>
      </div>
    </>
  );
}
