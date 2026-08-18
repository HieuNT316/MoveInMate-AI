import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatWidget from "./ChatWidget";
import MobileTabBar from "./MobileTabBar";
import { RESIDENT_NAV } from "../../lib/nav";

export default function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background">
      <Sidebar />

      <div className="flex-1 min-w-0 overflow-y-auto">
        <Header />

        <main className="mx-auto max-w-6xl px-4 py-6 pb-24 lg:px-8 lg:py-10 lg:pb-10">
          {children}
        </main>
      </div>

      <ChatWidget />
      <MobileTabBar items={RESIDENT_NAV} />
    </div>
  );
}
