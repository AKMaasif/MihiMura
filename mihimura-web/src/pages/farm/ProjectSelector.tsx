export function ProjectSelector({
  projects,
  value,
  onChange,
}: {
  projects: any[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label>
      Project
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select project</option>
        {projects.map((p) => (
          <option value={p.id} key={p.id}>
            {p.farm_name} · {p.crop}
          </option>
        ))}
      </select>
    </label>
  );
}
