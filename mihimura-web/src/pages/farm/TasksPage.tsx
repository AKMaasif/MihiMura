import { useEffect, useState } from 'react';
import { CalendarDays, ClipboardCheck, Clock3, Plus } from 'lucide-react';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function TasksPage() {
  const [tasks, setTasks] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [notifications, setNotifications] = useState<any[]>([]),
    [filter, setFilter] = useState('all'),
    [show, setShow] = useState(false),
    [notice, setNotice] = useState('');
  const [form, setForm] = useState<any>({
    project_id: '',
    title: 'Field observation',
    task_type: 'Observation',
    due_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    priority: 'medium',
    weather_dependency: '',
    instructions: '',
    assigned_to: 'Self',
  });
  const load = async () => {
    const [tasksResult, projectsResult, notificationsResult] = await Promise.allSettled([
      platformApi.tasks(),
      platformApi.projects(),
      platformApi.notifications(),
    ]);

    if (tasksResult.status === 'fulfilled') {
      setTasks(tasksResult.value);
    }

    if (projectsResult.status === 'fulfilled') {
      const projectList = projectsResult.value as any[];

      setProjects(projectList);

      setForm((x: any) => ({
        ...x,
        project_id: x.project_id || projectList[0]?.id || '',
      }));
    }

    if (notificationsResult.status === 'fulfilled') {
      setNotifications(notificationsResult.value);
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const patch = async (id: string, data: any) => {
    await platformApi.patchTask(id, data);
    await load();
  };
  const visible = filter === 'all' ? tasks : tasks.filter((x) => x.status === filter);
  const add = async () => {
    if (!form.project_id) {
      setNotice('Create a cultivation project before adding a task.');
      return;
    }
    const dueAt = new Date(form.due_at).toISOString();
    await platformApi.addTask({ ...form, due_at: dueAt });
    await platformApi.addNotification({
      channel: 'in-app',
      title: `Task reminder · ${form.title}`,
      body: `Scheduled for ${new Date(dueAt).toLocaleString()}. Weather dependency: ${form.weather_dependency || 'none recorded'}.`,
      scheduled_at: dueAt,
      status: 'scheduled',
    });
    setShow(false);
    setNotice('Task created and a notification event was scheduled.');
    await load();
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <ClipboardCheck /> Recommendations become operational work
          </span>
          <h2>Task & notification centre</h2>
          <p>
            Due windows, weather dependencies, assignment, completion evidence and rescheduling reasons remain
            attached to each task.
          </p>
        </div>
        <Button disabled={!projects.length} onClick={() => setShow(true)}>
          <Plus /> Add task
        </Button>
      </section>
      {notice && (
        <Notice tone="info" title="Task centre">
          {notice}
        </Notice>
      )}
      <div className="filter-tabs">
        {['all', 'pending', 'completed'].map((x) => (
          <button className={filter === x ? 'active' : ''} onClick={() => setFilter(x)} key={x}>
            {x}
          </button>
        ))}
      </div>
      <Card
        title="Execution queue"
        subtitle="Forecast-to-Task Autopilot proposes changes; the farmer retains the final decision"
      >
        {visible.length ? (
          <div className="task-table">
            {visible.map((t) => (
              <div key={t.id}>
                <i className={t.priority} />
                <div>
                  <b>{t.title}</b>
                  <p>{t.instructions || 'No additional instructions'}</p>
                  <small>
                    {t.farm_name} · {t.weather_dependency || 'No weather condition'}
                  </small>
                </div>
                <div className="task-due">
                  <Clock3 />
                  <span>{new Date(t.due_at).toLocaleString()}</span>
                </div>
                <Status
                  tone={t.status === 'completed' ? 'green' : t.priority === 'high' ? 'orange' : 'amber'}
                >
                  {t.status === 'completed' ? 'completed' : t.priority}
                </Status>
                <div className="task-actions">
                  {t.status !== 'completed' && (
                    <Button
                      onClick={() =>
                        void patch(t.id, {
                          status: 'completed',
                          completion_note: 'Completed by farmer from task centre',
                        })
                      }
                    >
                      Complete
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    onClick={() =>
                      void patch(t.id, {
                        due_at: new Date(Date.now() + 2 * 86400000).toISOString(),
                        schedule_reason: 'Farmer rescheduled after reviewing field/weather context',
                      })
                    }
                  >
                    +2 days
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No task in this view"
            detail={
              projects.length
                ? 'Create a task or ask MihiMura to convert a confirmed recommendation into one.'
                : 'Create a cultivation project first.'
            }
          />
        )}
      </Card>
      <Card
        title="Scheduled notification events"
        subtitle="Notification records are auditable; browser and server-side delivery providers can be added without changing task history"
      >
        {notifications.length ? (
          <div className="notification-event-list">
            {notifications.slice(0, 8).map((n) => (
              <div key={n.id}>
                <CalendarDays />
                <span>
                  <b>{n.title}</b>
                  <small>{n.body}</small>
                </span>
                <Status tone={n.status === 'sent' ? 'green' : 'blue'}>{n.status}</Status>
                <time>{new Date(n.scheduled_at || n.created_at).toLocaleString()}</time>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No notification events yet"
            detail="Creating a task schedules an auditable in-app reminder record. Add a standards-based push/SMS provider later for background delivery."
          />
        )}
      </Card>
      {show && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <header>
              <h2>Create task</h2>
              <button onClick={() => setShow(false)}>×</button>
            </header>
            <div className="field-grid">
              <label>
                Project
                <select
                  value={form.project_id}
                  onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                >
                  {projects.map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.farm_name} · {p.crop}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Task type
                <input
                  value={form.task_type}
                  onChange={(e) => setForm({ ...form, task_type: e.target.value })}
                />
              </label>
              <label className="full">
                Title
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </label>
              <label>
                Due
                <input
                  type="datetime-local"
                  value={form.due_at}
                  onChange={(e) => setForm({ ...form, due_at: e.target.value })}
                />
              </label>
              <label>
                Priority
                <select
                  value={form.priority}
                  onChange={(e) => setForm({ ...form, priority: e.target.value })}
                >
                  <option>low</option>
                  <option>medium</option>
                  <option>high</option>
                </select>
              </label>
              <label className="full">
                Weather dependency
                <input
                  value={form.weather_dependency}
                  onChange={(e) => setForm({ ...form, weather_dependency: e.target.value })}
                />
              </label>
              <label className="full">
                Instructions
                <textarea
                  value={form.instructions}
                  onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                />
              </label>
            </div>
            <div className="modal-actions">
              <Button variant="ghost" onClick={() => setShow(false)}>
                Cancel
              </Button>
              <Button onClick={() => void add()}>Create task</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
