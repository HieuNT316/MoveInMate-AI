"use client";

import { useState } from "react";
import {
  ChevronDown,
  Lock,
  Megaphone,
  Pin,
  PartyPopper,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import Layout from "../components/Layout";
import {
  CATEGORY_LABEL,
  mockAnnouncements,
  mockRegulations,
  type Announcement,
} from "../../lib/mockContent";

type Tab = "announcements" | "regulations";

const CATEGORY_ICON: Record<Announcement["category"], LucideIcon> = {
  general: Megaphone,
  maintenance: Wrench,
  event: PartyPopper,
  security: Lock,
};

export default function ContentPage() {
  const [tab, setTab] = useState<Tab>("announcements");
  const [expandedReg, setExpandedReg] = useState<string | null>(null);

  const pinned = mockAnnouncements.filter((a) => a.pinned);
  const rest = mockAnnouncements.filter((a) => !a.pinned);

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <h2 className="font-display text-xl font-semibold text-ink">
          Thông báo & Nội quy
        </h2>
        <p className="mt-1 text-sm text-muted">
          Thông tin từ Ban Quản Lý
        </p>

        <div className="mt-6 flex gap-2">
          <button
            onClick={() => setTab("announcements")}
            className={`flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium transition ${
              tab === "announcements"
                ? "border-ink bg-ink text-white"
                : "border-border text-muted hover:text-ink"
            }`}
          >
            Thông báo
            <span
              className={`rounded-full px-1.5 text-[11px] ${tab === "announcements" ? "bg-white/20" : "bg-background"}`}
            >
              {mockAnnouncements.length}
            </span>
          </button>
          <button
            onClick={() => setTab("regulations")}
            className={`rounded-full border px-4 py-1.5 text-xs font-medium transition ${
              tab === "regulations"
                ? "border-ink bg-ink text-white"
                : "border-border text-muted hover:text-ink"
            }`}
          >
            Nội quy
          </button>
        </div>

        {tab === "announcements" ? (
          <div className="mt-6 space-y-6">
            {pinned.length > 0 && (
              <div>
                <p className="mb-2.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-gold">
                  <Pin className="h-3 w-3" strokeWidth={2} />
                  Thông báo ghim
                </p>
                <div className="space-y-3">
                  {pinned.map((a) => (
                    <AnnouncementCard key={a.id} announcement={a} pinned />
                  ))}
                </div>
              </div>
            )}

            <div>
              <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
                Tất cả thông báo
              </p>
              <div className="space-y-3">
                {rest.map((a) => (
                  <AnnouncementCard key={a.id} announcement={a} />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {mockRegulations.map((reg) => {
              const isExpanded = expandedReg === reg.id;
              return (
                <div
                  key={reg.id}
                  className="overflow-hidden rounded-2xl border border-border bg-surface"
                >
                  <button
                    onClick={() => setExpandedReg(isExpanded ? null : reg.id)}
                    className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-ink">
                          {reg.title}
                        </p>
                        <span className="rounded-full bg-gold-tint px-2 py-0.5 text-[11px] text-gold">
                          {reg.version}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted">{reg.summary}</p>
                      <p className="mt-2 text-[11px] text-muted">
                        {reg.sections.length} điều khoản · Hiệu lực:{" "}
                        {reg.effectiveDate}
                      </p>
                    </div>
                    <ChevronDown
                      className={`mt-1 h-4 w-4 shrink-0 text-muted transition-transform ${isExpanded ? "rotate-180" : ""}`}
                      strokeWidth={2}
                    />
                  </button>

                  {isExpanded && (
                    <div className="space-y-4 border-t border-border px-5 py-4">
                      {reg.sections.map((s) => (
                        <div key={s.heading}>
                          <p className="text-xs font-semibold text-ink">
                            {s.heading}
                          </p>
                          <p className="mt-1 text-sm leading-relaxed text-muted">
                            {s.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}

function AnnouncementCard({
  announcement,
  pinned,
}: {
  announcement: (typeof mockAnnouncements)[number];
  pinned?: boolean;
}) {
  const Icon = CATEGORY_ICON[announcement.category];

  return (
    <div
      className={`rounded-2xl border p-5 ${pinned ? "border-gold/40 bg-gold-tint" : "border-border bg-surface"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium text-ink">{announcement.title}</p>
        <span className="flex items-center gap-1 rounded-full bg-background px-2 py-0.5 text-[11px] text-muted">
          <Icon className="h-3 w-3" strokeWidth={2} />
          {CATEGORY_LABEL[announcement.category]}
        </span>
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">
        {announcement.body}
      </p>
      <p className="mt-2 text-[11px] text-muted">
        {announcement.author} · {announcement.date}
      </p>
    </div>
  );
}
