import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { groups } from '../data';
import Collapsible from './Collapsible';

const allIds = groups.flatMap((g) => [g.id, ...g.subgroups.map((s) => `${g.id}/${s.id}`)]);

export default function Sidebar() {
  const [open, setOpen] = useState<Record<string, boolean>>(
    Object.fromEntries(allIds.map((id) => [id, true])),
  );
  const setAll = (v: boolean) => setOpen(Object.fromEntries(allIds.map((id) => [id, v])));
  const set = (id: string) => (v: boolean) => setOpen((o) => ({ ...o, [id]: v }));

  return (
    <nav className="sidebar">
      <div className="bulk">
        <button onClick={() => setAll(true)}>Expand all</button>
        <button onClick={() => setAll(false)}>Collapse all</button>
      </div>
      {groups.map((g) => (
        <Collapsible
          key={g.id} title={g.name}
          count={g.subgroups.reduce((n, s) => n + s.items.length, 0)}
          open={open[g.id]} onToggle={set(g.id)}
        >
          {g.subgroups.map((s) => (
            <Collapsible
              key={s.id} level={2} title={s.name} count={s.items.length}
              open={open[`${g.id}/${s.id}`]} onToggle={set(`${g.id}/${s.id}`)}
            >
              <ul>
                {s.items.map((it) => (
                  <li key={it.slug}>
                    <NavLink to={`/item/${it.slug}`}>{it.emoji} {it.name}</NavLink>
                  </li>
                ))}
              </ul>
            </Collapsible>
          ))}
        </Collapsible>
      ))}
    </nav>
  );
}
