import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatWidget from "./ChatWidget";
import MobileTabBar from "./MobileTabBar";
import { RESIDENT_NAV } from "../../lib/nav";

export default function Layout({
  children,
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="app-canvas flex h-[100dvh] overflow-hidden">
      <Sidebar />

      <div className="flex-1 min-w-0 overflow-y-auto">
        <Header />

        <main className={`page-content mx-auto px-4 py-6 pb-24 lg:py-10 lg:pb-10 ${wide ? "max-w-[1600px] lg:px-5" : "max-w-6xl lg:px-8"}`}>
          {children}
        </main>
      </div>

      <ChatWidget />
      <MobileTabBar items={RESIDENT_NAV} />
    </div>
  );
}
