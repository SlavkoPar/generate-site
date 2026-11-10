import { Link } from 'react-router-dom';
import { groups } from '../data';
import Collapsible from '../components/Collapsible';

export default function Home() {
  return (
    <>
      <h1>Fruits &amp; Vegetables</h1>
      <p>Click a heading to expand or collapse a group, and open any item for details.</p>
      {groups.map((g) => (
        <Collapsible key={g.id} title={g.name}>
          {g.subgroups.map((s) => (
            <Collapsible key={s.id} level={2} title={s.name} count={s.items.length} defaultOpen={false}>
              <div className="cards">
                {s.items.map((it) => (
                  <Link key={it.slug} className="card" to={`/item/${it.slug}`}>
                    <span className="emoji">{it.emoji}</span>
                    <span>{it.name}</span>
                  </Link>
                ))}
              </div>
            </Collapsible>
          ))}
        </Collapsible>
      ))}
    </>
  );
}
