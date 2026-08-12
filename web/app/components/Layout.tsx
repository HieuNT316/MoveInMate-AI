import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatWidget from "./ChatWidget";

export default function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <Header />

        <main className="mx-auto max-w-6xl px-8 py-10">{children}</main>
      </div>

      <ChatWidget />
    </div>
  );
}