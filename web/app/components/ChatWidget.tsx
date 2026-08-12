"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Maximize2, Send, Sparkles, X } from "lucide-react";

import Button from "./Button";
import { api, describeError, type Source } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  sources?: Source[];
  refused?: boolean;
};

const GREETING: Message = {
  id: 0,
  role: "assistant",
  text: "Xin chào 👋 Tôi là MoveInMate AI. Hỏi tôi bất kỳ thủ tục nào liên quan đến việc nhận nhà.",
};

/** Bong bóng chat nổi — dùng lại đúng API thật của trang /chat, chỉ gọn hơn. */
export default function ChatWidget() {
  const pathname = usePathname();
  const { userId } = useDemoUser();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, open]);

  if (pathname === "/chat" || pathname === "/login") return null;

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || sending) return;

    setMessages((prev) => [
      ...prev,
      { id: prev.length + 1, role: "user", text: question },
    ]);
    setInput("");
    setSending(true);

    try {
      const reply = await api.sendChat(userId, question);
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          text: reply.answer,
          sources: reply.sources,
          refused: reply.answer_source === "no_context",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          text: describeError(err),
          refused: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="mb-3 flex h-[520px] w-[360px] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_20px_50px_-12px_rgba(0,45,98,0.35)]">
          <div className="flex items-center gap-3 border-b border-border bg-ink px-4 py-3.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
              <Bot className="h-4 w-4 text-gold-soft" strokeWidth={1.75} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-display text-sm font-semibold text-white">
                MoveInMate AI
              </p>
              <p className="flex items-center gap-1.5 text-[11px] text-white/60">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
                Đang hoạt động
              </p>
            </div>
            <Link
              href="/chat"
              title="Mở toàn màn hình"
              className="rounded-lg p-1.5 text-white/60 transition hover:bg-white/10 hover:text-white"
            >
              <Maximize2 className="h-3.5 w-3.5" strokeWidth={1.75} />
            </Link>
            <button
              onClick={() => setOpen(false)}
              aria-label="Đóng"
              className="rounded-lg p-1.5 text-white/60 transition hover:bg-white/10 hover:text-white"
            >
              <X className="h-3.5 w-3.5" strokeWidth={1.75} />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="max-w-[85%]">
                  <div
                    className={`rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                      message.role === "user"
                        ? "rounded-br-sm bg-ink text-white"
                        : message.refused
                          ? "rounded-bl-sm border border-gold/40 bg-gold-tint text-ink"
                          : "rounded-bl-sm border border-border bg-background text-ink"
                    }`}
                  >
                    {message.text}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <p className="mt-1 text-[10px] text-muted">
                      📄 {message.sources.map((s) => s.title).join(" · ")}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <p className="text-xs text-muted">Đang tra cứu tài liệu...</p>
            )}
            {messages.length === 1 && (
              <button
                onClick={() => send("Làm thẻ xe cần giấy tờ gì?")}
                className="flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-[11px] text-muted transition hover:border-gold/50 hover:text-gold"
              >
                <Sparkles className="h-3 w-3" strokeWidth={1.75} />
                Làm thẻ xe cần giấy tờ gì?
              </button>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-border p-3">
            <div className="flex items-center gap-2">
              <input
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-ink placeholder:text-muted focus:border-gold/50 focus:outline-none"
                placeholder="Nhập câu hỏi..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(input)}
              />
              <Button
                onClick={() => send(input)}
                disabled={sending}
                aria-label="Gửi"
                size="icon"
                className="rounded-lg"
              >
                <Send className="h-3.5 w-3.5" strokeWidth={1.75} />
              </Button>
            </div>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Đóng trợ lý AI" : "Mở trợ lý AI"}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-gold text-white shadow-[0_12px_28px_-8px_rgba(0,86,210,0.6)] transition hover:bg-ink-soft"
      >
        {open ? (
          <X className="h-5 w-5" strokeWidth={2} />
        ) : (
          <Bot className="h-6 w-6" strokeWidth={1.75} />
        )}
      </button>
    </div>
  );
}
