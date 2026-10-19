import { useEffect, useMemo, useState } from 'react';
import { Activity, CircleDollarSign, Waves } from 'lucide-react';
import { Button, Card, Empty, Metric } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { ProjectSelector } from './ProjectSelector';

export function ExpensesPage() {
  const [items, setItems] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [projectId, setProjectId] = useState(''),
    [amount, setAmount] = useState(2500),
    [category, setCategory] = useState('Labour'),
    [note, setNote] = useState('');
  const load = async () => {
    const r = await Promise.allSettled([platformApi.expenses(), platformApi.projects()]);
    if (r[0].status === 'fulfilled') setItems(r[0].value);
    if (r[1].status === 'fulfilled') {
      setProjects(r[1].value);
      if (!projectId && r[1].value[0]) setProjectId(r[1].value[0].id);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const visible = items.filter((x) => !projectId || x.project_id === projectId);
  const total = useMemo(() => visible.reduce((s, x) => s + Number(x.amount || 0), 0), [visible]);
  const project = projects.find((x) => x.id === projectId);
  const budget = Number(project?.budget || 0);
  const add = async () => {
    if (!projectId) return;
    await platformApi.addExpense({ project_id: projectId, amount, category, note });
    setNote('');
    await load();
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <CircleDollarSign /> Field economics
          </span>
          <h2>Expenses</h2>
          <p>
            Track costs against the selected crop digital twin so recommendations can account for
            affordability and season outcomes.
          </p>
        </div>
        <ProjectSelector projects={projects} value={projectId} onChange={setProjectId} />
      </section>
      <div className="dashboard-metrics">
        <Metric
          label="Recorded costs"
          value={`LKR ${total.toLocaleString()}`}
          note={project?.farm_name || 'Select a project'}
          icon={CircleDollarSign}
          tone="purple"
        />
        <Metric
          label="Project budget"
          value={budget ? `LKR ${budget.toLocaleString()}` : '—'}
          note="Farmer-defined budget"
          icon={Activity}
        />
        <Metric
          label="Budget used"
          value={budget ? `${Math.round((total / budget) * 100)}%` : '—'}
          note="Based on recorded costs"
          icon={Waves}
          tone="orange"
        />
      </div>
      <div className="two-col">
        <Card title="Record expense">
          <div className="field-grid">
            <ProjectSelector projects={projects} value={projectId} onChange={setProjectId} />
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option>Labour</option>
                <option>Seed</option>
                <option>Fertilizer</option>
                <option>Irrigation</option>
                <option>Machinery</option>
                <option>Transport</option>
                <option>Other</option>
              </select>
            </label>
            <label>
              Amount (LKR)
              <input
                type="number"
                min="0"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </label>
            <label className="full">
              Note
              <input value={note} onChange={(e) => setNote(e.target.value)} />
            </label>
          </div>
          <Button disabled={!projectId || amount <= 0} onClick={() => void add()}>
            Save expense
          </Button>
        </Card>
        <Card title="Expense history">
          {visible.length ? (
            <div className="expense-list">
              {visible.map((x) => (
                <div key={x.id}>
                  <span>
                    <b>{x.category}</b>
                    <small>{new Date(x.created_at).toLocaleDateString()}</small>
                  </span>
                  <strong>LKR {Number(x.amount).toLocaleString()}</strong>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="No expenses recorded" />
          )}
        </Card>
      </div>
    </>
  );
}
