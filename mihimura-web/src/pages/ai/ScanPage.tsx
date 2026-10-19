import { useEffect, useRef, useState } from 'react';
import { Camera, FileImage, ShieldCheck, Stethoscope } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';

export function ScanPage() {
  const nav = useNavigate();
  const { profile } = useAuth();
  const { language } = useLanguage();
  const [files, setFiles] = useState<File[]>([]),
    [previews, setPreviews] = useState<string[]>([]),
    [crop, setCrop] = useState('Auto-detect'),
    [symptoms, setSymptoms] = useState(''),
    [affected, setAffected] = useState(10),
    [firstObserved, setFirstObserved] = useState(''),
    [irrigation, setIrrigation] = useState('Normal'),
    [recentInputs, setRecentInputs] = useState(''),
    [projects, setProjects] = useState<any[]>([]),
    [projectId, setProjectId] = useState(''),
    [result, setResult] = useState<any>(null),
    [loading, setLoading] = useState(false),
    [notice, setNotice] = useState('');
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    platformApi
      .projects()
      .then((x: any[]) => {
        setProjects(x);
        if (x[0]) {
          setProjectId(x[0].id);
          setCrop(x[0].crop || 'Auto-detect');
        }
      })
      .catch(() => setProjects([]));
  }, []);
  useEffect(() => () => previews.forEach(URL.revokeObjectURL), [previews]);
  const choose = (e: any) => {
    const selected = Array.from(e.target.files || []) as File[];
    const valid = selected.filter((x) => ['image/jpeg', 'image/png', 'image/webp'].includes(x.type));
    if (valid.length !== selected.length) setNotice('Only JPEG, PNG and WebP images are accepted.');
    const next = [...files, ...valid].slice(0, 4);
    setFiles(next);
    setPreviews(next.map(URL.createObjectURL));
    e.target.value = '';
  };
  const remove = (i: number) => {
    const next = files.filter((_, j) => j !== i);
    setFiles(next);
    setPreviews(next.map(URL.createObjectURL));
  };
  const contextText = `${symptoms || 'No symptom text provided'}; affected about ${affected}%; first observed ${firstObserved || 'unknown'}; irrigation ${irrigation}; recent inputs ${recentInputs || 'none reported'}; region ${profile?.district || 'unknown'}`;
  const run = async () => {
    if (!files.length) return;
    setLoading(true);
    setNotice('');
    try {
      setResult(await platformApi.diagnose(files, crop, contextText, projectId, language));
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setLoading(false);
    }
  };
  const expert = async () => {
    if (!result) return;
    if (!projectId) {
      setNotice('Select a project before creating an expert evidence case.');
      return;
    }
    await platformApi.addExpertCase({
      project_id: projectId,
      urgency: result.expert_review ? 'high' : 'medium',
      reason: `Crop scan review: ${result?.differential?.[0]?.condition || 'uncertain condition'}`,
      evidence: `${result.image_count || files.length} images · crop ${result.crop} · confidence ${Math.round((result.crop_confidence || 0) * 100)}% · symptoms ${(result.observed_symptoms || []).join(', ')}`,
      preferred_language: profile?.language || 'English',
    });
    nav('/app/expert');
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Camera /> Guided multimodal evidence
          </span>
          <h2>Crop health scan</h2>
          <p>
            A safer assessment combines up to four viewpoints with symptoms, timing, irrigation, recent
            treatments and project context.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Crop Health Scan">
          {notice}
        </Notice>
      )}
      <div className="scan-layout">
        <Card
          title="1. Capture the evidence"
          subtitle="Leaf front, leaf back, whole plant and field-wide views"
        >
          <div className="image-slot-grid">
            {['Leaf front', 'Leaf back', 'Whole plant', 'Field-wide'].map((label, i) => (
              <button
                key={label}
                className={`image-slot ${previews[i] ? 'filled' : ''}`}
                onClick={() => (previews[i] ? remove(i) : input.current?.click())}
              >
                {previews[i] ? (
                  <>
                    <img src={previews[i]} alt={label} />
                    <span className="image-remove">Remove</span>
                  </>
                ) : (
                  <>
                    <FileImage />
                    <b>{label}</b>
                    <span>{i === 0 ? 'Required' : 'Recommended'}</span>
                  </>
                )}
              </button>
            ))}
          </div>
          <input
            ref={input}
            hidden
            multiple
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={choose}
          />
          <div className="field-grid">
            <label>
              Crop
              <select value={crop} onChange={(e) => setCrop(e.target.value)}>
                <option>Auto-detect</option>
                <option>Chilli</option>
                <option>Paddy</option>
                <option>Tomato</option>
                <option>Brinjal</option>
                <option>Maize</option>
              </select>
            </label>
            <label>
              Affected area <b>{affected}%</b>
              <input
                type="range"
                min="1"
                max="100"
                value={affected}
                onChange={(e) => setAffected(Number(e.target.value))}
              />
            </label>
            <label className="full">
              Symptoms
              <textarea
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="Describe discoloration, lesions, wilting, insects, field pattern…"
              />
            </label>
            <label>
              First observed
              <input type="date" value={firstObserved} onChange={(e) => setFirstObserved(e.target.value)} />
            </label>
            <label>
              Irrigation status
              <select value={irrigation} onChange={(e) => setIrrigation(e.target.value)}>
                <option>Normal</option>
                <option>Dry</option>
                <option>Waterlogged</option>
                <option>Unknown</option>
              </select>
            </label>
            <label>
              Recent fertilizer / pesticide
              <input
                value={recentInputs}
                onChange={(e) => setRecentInputs(e.target.value)}
                placeholder="None / describe without guessing rates"
              />
            </label>
            <label>
              Project
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">No project / general scan</option>
                {projects.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.farm_name} · {p.crop} · {p.stage}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Button disabled={!files.length || loading} onClick={() => void run()}>
            {loading ? (
              'Vision agent is comparing evidence…'
            ) : (
              <>
                {' '}
                Analyse {files.length || ''} guided image{files.length === 1 ? '' : 's'}
              </>
            )}
          </Button>
        </Card>
        <Card
          title="2. Differential assessment"
          subtitle="Ranked possibilities with uncertainty and next evidence"
        >
          {result ? (
            <div className="diagnosis">
              <div className="diagnosis-top">
                <div>
                  <small>Likely crop</small>
                  <h3>{result.crop}</h3>
                  <span>
                    {Math.round((result.crop_confidence || 0) * 100)}% crop confidence ·{' '}
                    {result.image_count || files.length} image(s)
                  </span>
                </div>
                <Status tone={result.expert_review ? 'orange' : 'amber'}>{result.urgency}</Status>
              </div>
              <div className="quality-line">
                <ShieldCheck />
                <span>Evidence quality</span>
                <b>{result.quality}</b>
              </div>
              <section>
                <h4>Observed symptoms</h4>
                <div className="tag-row">
                  {(result.observed_symptoms || []).map((x: string) => (
                    <span key={x}>{x}</span>
                  ))}
                </div>
              </section>
              <section>
                <h4>Possible conditions</h4>
                <div className="differential-list">
                  {(result.differential || []).map((x: any, i: number) => (
                    <div key={`${x.condition}-${i}`}>
                      <i>0{i + 1}</i>
                      <span>
                        <b>{x.condition}</b>
                        <p>{x.evidence}</p>
                      </span>
                      <strong>{Math.round((x.confidence || 0) * 100)}%</strong>
                    </div>
                  ))}
                </div>
              </section>
              <section>
                <h4>Immediate low-risk steps</h4>
                <ul>
                  {(result.safe_steps || []).map((x: string) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </section>
              {result.additional_evidence_needed?.length > 0 && (
                <section>
                  <h4>Evidence still needed</h4>
                  <div className="tag-row">
                    {result.additional_evidence_needed.map((x: string) => (
                      <span key={x}>{x}</span>
                    ))}
                  </div>
                </section>
              )}
              <Notice tone="warning" title="Diagnosis safeguard">
                {result.disclaimer}
              </Notice>
              <div className="decision-actions">
                <Button
                  variant="secondary"
                  disabled={!projectId}
                  onClick={async () => {
                    if (!projectId) return;
                    await platformApi.addTask({
                      project_id: projectId,
                      title: 'Collect crop-scan follow-up evidence',
                      task_type: 'Crop observation',
                      due_at: new Date(Date.now() + 24 * 3600e3).toISOString(),
                      priority: 'medium',
                      instructions: (result.safe_steps || []).join('; '),
                      weather_dependency: 'Field observation when safe',
                    });
                    nav('/app/tasks');
                  }}
                >
                  Create observation task
                </Button>
                <Button disabled={!projectId} onClick={() => void expert()}>
                  <Stethoscope /> Request expert review
                </Button>
              </div>
            </div>
          ) : (
            <Empty
              title="No analysis yet"
              detail="Add at least one clear image and symptom context. Multiple guided images improve the evidence package."
            />
          )}
        </Card>
      </div>
    </>
  );
}
