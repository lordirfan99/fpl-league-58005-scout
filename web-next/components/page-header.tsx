import { Clock3 } from "lucide-react";

export function PageHeader({ eyebrow, title, description, updated }: { eyebrow: string; title: string; description: string; updated?: string }) {
  return <header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div><div className="freshness"><Clock3 size={15} /><span>{updated ? `Updated ${updated}` : "Live snapshot"}</span></div></header>;
}
