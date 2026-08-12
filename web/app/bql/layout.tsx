"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import BQLLayout from "../components/BQLLayout";
import { api, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

export default function BQLRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    if (!ready) return;
    api
      .getProfile(userId)
      .then((me) => {
        if (me.role !== "admin") {
          router.replace("/dashboard");
          return;
        }
        setProfile(me);
      })
      .catch(() => setProfile(null));
  }, [ready, userId, router]);

  if (!profile) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải...
      </div>
    );
  }

  return <BQLLayout>{children}</BQLLayout>;
}
