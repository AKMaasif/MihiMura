import { useEffect, useState } from 'react';
import { Send, Users } from 'lucide-react';
import { Card, Notice, Status, Button, Empty } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';

export function CommunityPage() {
  const { profile } = useAuth();
  const [items, setItems] = useState<any[]>([]),
    [note, setNote] = useState(''),
    [type, setType] = useState('pest sighting'),
    [sent, setSent] = useState(false),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    platformApi
      .community()
      .then((rows) => {
        setItems(Array.isArray(rows) ? rows : []);
        setError('');
      })
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : 'Community signals could not be loaded.');
      })
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    void load();
  }, []);
  const submit = async () => {
    if (!note.trim()) return;
    if (!profile?.district) {
      setError('Add a district to your profile before sending a community signal.');
      return;
    }
    setError('');
    try {
      await platformApi.addCommunity({
        district: profile.district,
        crop: Array.isArray(profile?.primary_crops_json) ? profile.primary_crops_json[0] || 'Chilli' : 'Chilli',
        report_type: type,
        severity: 'watch',
        note,
        lat: profile?.lat,
        lon: profile?.lon,
      });
      setNote('');
      setSent(true);
      load();
    } catch (e) {
      setSent(false);
      setError(e instanceof Error ? e.message : 'The signal was not saved.');
    }
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Users /> Privacy-preserving field network
          </span>
          <h2>Community Sentinel Swarm</h2>
          <p>
            Individual observations remain private. Regional alerts publish only after minimum-count, quality
            and expert-verification rules.
          </p>
        </div>
      </section>
      <div className="two-col">
        <Card
          title="Report a local observation"
          subtitle="Your exact identity and boundary are not published"
        >
          <label>
            Observation type
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option>pest sighting</option>
              <option>leaf symptom</option>
              <option>flood observation</option>
              <option>irrigation failure</option>
              <option>wind damage</option>
            </select>
          </label>
          <label>
            What did you observe?
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Describe what you saw, approximate affected area and crop stage…"
            />
          </label>
          <Button onClick={() => void submit()}>
            <Send /> Submit anonymized signal
          </Button>
          {sent && (
            <Notice tone="success" title="Signal queued">
              It will contribute only after privacy and quality thresholds are satisfied.
            </Notice>
          )}
        </Card>
        <Card title="Regional watch signals" subtitle="Published clusters—not individual farmer reports">
          {error && (
            <Notice tone="warning" title="Community signals">
              {error}{' '}
              <button type="button" onClick={() => load()}>
                Retry
              </button>
            </Notice>
          )}
          {loading ? (
            <div className="page-loading">Loading published signals…</div>
          ) : items.length ? (
            <div className="community-list">
              {items.map((x) => (
                <div key={x.id}>
                  <Users />
                  <span>
                    <b>
                      {x.district} · {x.crop || 'Mixed crops'}
                    </b>
                    <p>
                      {x.report_type}: {x.note}
                    </p>
                  </span>
                  <Status tone={x.severity === 'high' ? 'orange' : 'amber'}>{x.severity}</Status>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title={error ? 'Signals could not be loaded' : 'No regional cluster is above publication threshold'}
              detail={
                error
                  ? 'Retry after the API is reachable. Sample clusters are not shown in their place.'
                  : 'This is a positive state; individual reports remain private.'
              }
            />
          )}
        </Card>
      </div>
      <Card title="How the swarm avoids false alarms">
        <div className="sentinel-steps">
          {[
            ['1', 'Collect', 'Anonymized local reports'],
            ['2', 'Quality gate', 'Duplicates, location and plausibility'],
            ['3', 'Minimum count', 'Suppress small groups'],
            ['4', 'Cross-check', 'Weather, crop and other evidence'],
            ['5', 'Expert review', 'For serious outbreak / quarantine concerns'],
            ['6', 'Publish', 'Measured wording + recommended observation'],
          ].map((x) => (
            <div key={x[0]}>
              <i>{x[0]}</i>
              <b>{x[1]}</b>
              <span>{x[2]}</span>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
