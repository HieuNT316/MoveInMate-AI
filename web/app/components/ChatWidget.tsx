"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, FileText, Maximize2, Send, Sparkles, X } from "lucide-react";

import Button from "./Button";
import { api, describeError, CHAT_AUTO_OPEN_KEY, type Source } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { linkifyText } from "../../lib/linkify";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  sources?: Source[];
  refused?: boolean;
  /** Nút hành động dưới bong bóng — vd nhảy thẳng tới mục checklist đang dở.
   * Tính tất định từ checklist đã tải, KHÔNG phải LLM tự suy ra. */
  actionHref?: string;
  actionLabel?: string;
};

const GREETING: Message = {
  id: 0,
  role: "assistant",
  text: "Xin chào, tôi là MoveInMate AI. Hỏi tôi bất kỳ thủ tục nào liên quan đến việc nhận nhà.",
};

/** Bong bóng chat nổi — dùng lại đúng API thật của trang /chat, chỉ gọn hơn. */
export default function ChatWidget() {
  const pathname = usePathname();
  const { userId } = useDemoUser();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  // Giữ trong state của widget — mở/đóng bong bóng không mất, nhưng KHÔNG
  // lưu localStorage: đóng tab hay bấm "Mở toàn màn hình" (sang /chat) đều
  // nên bắt đầu hội thoại mới, tránh nhầm ngữ cảnh giữa hai nơi hỏi khác nhau.
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, open]);

  // Tự bung bong bóng chat khi vào Tổng quan — cư dân đăng nhập xong hay
  // mơ hồ không biết bắt đầu từ đâu. `sessionStorage` (không phải
  // localStorage) để chỉ bung 1 lần mỗi phiên làm việc: qua lại giữa các
  // trang trong cùng tab không bị bung lại làm phiền, đăng nhập phiên mới
  // (tab mới) thì bung lại.
  //
  // Lời chào chung chung ("tôi là AI, hỏi gì cũng được") không trả lời được
  // câu "vào đây làm gì" — nên khi tự bung, thay hẳn nội dung bằng VIỆC CỤ
  // THỂ cần làm tiếp theo, lấy thẳng từ checklist thật (giống banner "Việc
  // tiếp theo của bạn" ở /dashboard), kèm nút bấm nhảy đúng tới đó.
  useEffect(() => {
    if (pathname !== "/dashboard") return;
    if (sessionStorage.getItem(CHAT_AUTO_OPEN_KEY)) return;
    sessionStorage.setItem(CHAT_AUTO_OPEN_KEY, "1");
    setOpen(true);

    api
      .getChecklist(userId)
      .then((checklist) => {
        const nextItem = checklist.items.find((item) => !item.completed);
        setMessages([
          nextItem
            ? {
                id: 0,
                role: "assistant",
                text: `Xin chào, việc tiếp theo bạn cần làm là "${nextItem.task_name}". Bấm nút bên dưới để tới đúng bước đó, hoặc hỏi tôi bất cứ điều gì về thủ tục nhận nhà.`,
                actionHref: `/checklist?item=${nextItem.id}`,
                actionLabel: `Đến bước: ${nextItem.task_name}`,
              }
            : {
                id: 0,
                role: "assistant",
                text: "Xin chào, bạn đã hoàn tất toàn bộ checklist rồi! Có thắc mắc gì về thủ tục nhận nhà cứ hỏi tôi nhé.",
              },
        ]);
      })
      .catch(() => {
        // Không lấy được checklist (chưa onboarding, backend lỗi...) — giữ
        // nguyên lời chào mặc định thay vì chặn cả bong bóng chat.
      });
  }, [pathname, userId]);

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
      const reply = await api.sendChat(userId, question, conversationId ?? undefined);
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
      setConversationId(reply.conversation_id);
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
    <div className="fixed bottom-6 right-6 z-50 hidden lg:block">
      {open && (
        <div className="mb-3 flex h-[520px] w-[360px] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_20px_50px_-12px_rgba(0,45,98,0.35)]">
          <div className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-tint">
              <Bot className="h-4 w-4 text-gold" strokeWidth={1.75} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-display text-sm font-semibold text-ink">
                MoveInMate AI
              </p>
              <p className="flex items-center gap-1.5 text-[11px] text-muted">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
                Đang hoạt động
              </p>
            </div>
            <Link
              href="/chat"
              title="Mở toàn màn hình"
              className="rounded-lg p-1.5 text-muted transition hover:bg-background hover:text-ink"
            >
              <Maximize2 className="h-3.5 w-3.5" strokeWidth={1.75} />
            </Link>
            <button
              onClick={() => setOpen(false)}
              aria-label="Đóng"
              className="rounded-lg p-1.5 text-muted transition hover:bg-background hover:text-ink"
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
                    className={`whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                      message.role === "user"
                        ? "rounded-br-sm bg-ink text-white"
                        : message.refused
                          ? "rounded-bl-sm border border-gold/40 bg-gold-tint text-ink"
                          : "rounded-bl-sm border border-border bg-background text-ink"
                    }`}
                  >
                    {linkifyText(message.text)}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <p className="mt-1 flex items-center gap-1 text-[10px] text-muted">
                      <FileText className="h-2.5 w-2.5 shrink-0" strokeWidth={1.75} />
                      {message.sources.map((s) => s.title).join(" · ")}
                    </p>
                  )}
                  {message.actionHref && message.actionLabel && (
                    <Link
                      href={message.actionHref}
                      className="mt-2 flex items-center justify-center gap-1.5 rounded-lg bg-gold px-3 py-2 text-center text-[12px] font-medium text-white transition hover:bg-gold-soft"
                    >
                      {message.actionLabel} →
                    </Link>
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

      {/* Panel mở sẵn có nút X riêng trên header để đóng — hiện thêm nút tròn
          to này đè lên là hai nút đóng trùng nhau, thừa và nặng mắt. Ẩn hẳn
          lúc mở, chỉ dùng để MỞ lại khi đã đóng. */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Mở trợ lý AI"
          className="flex h-14 w-14 items-center justify-center rounded-full bg-gold text-white shadow-[0_12px_28px_-8px_rgba(0,86,210,0.6)] transition hover:bg-ink-soft"
        >
          <Bot className="h-6 w-6" strokeWidth={1.75} />
        </button>
      )}
    </div>
  );
}
