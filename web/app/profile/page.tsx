import Layout from "../components/Layout";
import { Building2, Home, BadgeCheck, Mail } from "lucide-react";

export default function ProfilePage() {
  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <div className="overflow-hidden rounded-2xl border border-border bg-surface">
          <div className="bg-ink px-8 py-10">
            <div className="flex items-center gap-5">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-gold/40 bg-gold/15 font-display text-3xl text-gold-soft">
                M
              </div>

              <div>
                <h2 className="font-display text-2xl font-semibold text-white">
                  Minh Thu
                </h2>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-white/50">
                  <Mail className="h-3.5 w-3.5" strokeWidth={1.75} />
                  minhthu@gmail.com
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 p-8 sm:grid-cols-3">
            <div className="rounded-xl border border-border p-5">
              <Building2 className="h-4 w-4 text-gold" strokeWidth={1.75} />
              <p className="mt-3 text-xs uppercase tracking-wide text-muted">Tòa</p>
              <p className="font-display mt-1 text-lg font-semibold text-ink">A1</p>
            </div>

            <div className="rounded-xl border border-border p-5">
              <Home className="h-4 w-4 text-gold" strokeWidth={1.75} />
              <p className="mt-3 text-xs uppercase tracking-wide text-muted">Căn hộ</p>
              <p className="font-display mt-1 text-lg font-semibold text-ink">1208</p>
            </div>

            <div className="rounded-xl border border-border p-5">
              <BadgeCheck className="h-4 w-4 text-emerald" strokeWidth={1.75} />
              <p className="mt-3 text-xs uppercase tracking-wide text-muted">Trạng thái</p>
              <p className="font-display mt-1 text-lg font-semibold text-emerald">
                Đang nhận nhà
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
