import BQLSidebar from "./BQLSidebar";
import Header from "./Header";
import MobileTabBar from "./MobileTabBar";
import { BQL_NAV } from "../../lib/nav";

export default function BQLLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="app-canvas flex h-[100dvh] overflow-hidden">
      <BQLSidebar />

      <div className="flex-1 min-w-0 overflow-y-auto">
        <Header />

        <main className="page-content mx-auto max-w-6xl px-4 py-6 pb-24 lg:px-8 lg:py-10 lg:pb-10">
          {children}
        </main>
      </div>

      <MobileTabBar items={BQL_NAV} />
    </div>
  );
}
