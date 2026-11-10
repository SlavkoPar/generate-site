import { Link, useParams } from 'react-router-dom';
import { findItem } from '../data';
import NotFound from './NotFound';

export default function ItemPage() {
  const { slug = '' } = useParams();
  const item = findItem(slug);
  if (!item) return <NotFound />;
  return (
    <article>
      <p><Link to="/">← Back</Link></p>
      <div className="hero">{item.emoji}</div>
      <h1>{item.name}</h1>
      <p className="muted">{item.groupName} · Season: {item.season}</p>
      <p>{item.description}</p>
      <h2>Key nutrients</h2>
      <ul>{item.nutrients.map((n) => <li key={n}>{n}</li>)}</ul>
    </article>
  );
}
