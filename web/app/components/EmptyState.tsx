import { Inbox, type LucideIcon } from "lucide-react";

export default function EmptyState({ title, description, hint, icon: Icon = Inbox }: { title: string; description?: string; hint?: string; icon?: LucideIcon }) {
  const detail = description ?? hint;
  return <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-14 text-center"><div className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-slate-500 shadow-sm"><Icon className="h-5 w-5" /></div><h3 className="mt-4 text-sm font-semibold text-slate-800">{title}</h3>{detail && <p className="mt-1 max-w-md text-sm leading-6 text-slate-500">{detail}</p>}</div>;
}
