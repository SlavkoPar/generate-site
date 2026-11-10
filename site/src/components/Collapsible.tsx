import { ReactNode, useState } from 'react';

interface Props {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  open?: boolean;
  onToggle?: (open: boolean) => void;
  level?: 1 | 2;
  children: ReactNode;
}

/** Expand/collapse section; controlled when `open` is given, otherwise self-managed. */
export default function Collapsible({
  title, count, defaultOpen = true, open, onToggle, level = 1, children,
}: Props) {
  const [inner, setInner] = useState(defaultOpen);
  const isOpen = open ?? inner;
  const toggle = () => {
    onToggle?.(!isOpen);
    if (open === undefined) setInner(!isOpen);
  };
  return (
    <section className={`group level-${level}`}>
      <button className="group-head" aria-expanded={isOpen} onClick={toggle}>
        <span className={`chev ${isOpen ? 'open' : ''}`}>▶</span>
        <span>{title}</span>
        {count !== undefined && <span className="count">{count}</span>}
      </button>
      {isOpen && <div className="group-body">{children}</div>}
    </section>
  );
}
