import BQLSidebar from "./BQLSidebar";
import Header from "./Header";

export default function BQLLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <BQLSidebar />

      <div className="flex-1 min-w-0">
        <Header />

        <main className="mx-auto max-w-6xl px-8 py-10">{children}</main>
      </div>
    </div>
  );
}
