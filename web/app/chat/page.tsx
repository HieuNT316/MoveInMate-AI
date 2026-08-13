"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, FileText, Loader2, Scale, Send, Sparkles } from "lucide-react";

import Layout from "../components/Layout";
import { api, type ChatHistoryEntry, type Source } from "../../lib/api";
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
  text: "Xin chào 👋 Tôi là MoveInMate AI. Hỏi tôi bất kỳ thủ tục nào liên quan đến việc nhận nhà — mọi câu trả lời đều kèm nguồn tài liệu.",
};

const SUGGESTIONS = [
  "Làm thẻ xe cần giấy tờ gì?",
  "Hồ sơ làm thẻ cư dân gồm những gì?",
  "Đăng ký tạm trú thế nào?",
];

/** Mỗi lượt hỏi đáp đã lưu tách thành 2 bong bóng (hỏi + đáp) để dùng chung
 * cách render với tin nhắn trong phiên hiện tại. `entries` đã sắp theo thời
 * gian tăng dần từ backend nên chỉ cần map tuần tự, không cần sort lại. */
function historyToMessages(entries: ChatHistoryEntry[]): Message[] {
  return entries.flatMap((entry, index) => [
    { id: index * 2, role: "user" as const, text: entry.question },
    {
      id: index * 2 + 1,
      role: "assistant" as const,
      text: entry.answer,
      sources: entry.sources,
      refused: entry.answer_source === "no_context",
    },
  ]);
}

export default function ChatPage() {
  const { userId, ready } = useDemoUser();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      const entries = await api.getChatHistory(userId);
      // Có lịch sử thật thì bỏ lời chào, coi như nối tiếp cuộc trò chuyện cũ
      // — chưa từng hỏi gì thì vẫn giữ lời chào cho người dùng lần đầu.
      setMessages(entries.length > 0 ? historyToMessages(entries) : [GREETING]);
    } catch (err) {
      // Không chặn cả trang chỉ vì không tải được lịch sử cũ — cư dân vẫn
      // phải hỏi được câu mới ngay cả khi backend đang chập chờn lúc này.
      console.error("[chat] không tải được lịch sử:", err);
    } finally {
      setLoadingHistory(false);
    }
  }, [userId]);

  useEffect(() => {
    if (ready) loadHistory();
  }, [ready, loadHistory]);

  const send = async (text: string) => {
    const question = text.trim();
    // `ready` false = chưa có danh tính, đang trên đường chuyển về /login.
    // `loadingHistory` true = lịch sử cũ chưa nạp xong; gửi sớm hơn thì lúc
    // nạp xong sẽ ghi đè cả tin nhắn vừa gửi (setMessages thay nguyên mảng).
    if (!question || sending || !ready || loadingHistory) return;

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
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          text: "Không kết nối được backend. Kiểm tra server đã chạy chưa.",
          refused: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <Layout>
      <div className="flex h-[calc(100vh-9rem)] flex-col overflow-hidden rounded-2xl border border-border bg-surface">
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ink">
            <Bot className="h-5 w-5 text-gold-soft" strokeWidth={1.75} />
          </div>
          <div>
            <p className="font-display text-base font-semibold text-ink">
              MoveInMate AI
            </p>
            <p className="flex items-center gap-1.5 text-xs text-emerald">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
              Đang hoạt động
            </p>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
          {loadingHistory && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Đang tải lịch sử trò chuyện...
            </div>
          )}

          {!loadingHistory && messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div className="max-w-lg">
                <div
                  className={`rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
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
                  <div className="mt-2 space-y-1.5">
                    <p className="text-[11px] uppercase tracking-wider text-muted">
                      Nguồn trích dẫn
                    </p>
                    {message.sources.map((source) => (
                      <SourceCard key={source.document_id} source={source} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Đang tra cứu tài liệu...
            </div>
          )}

          {!loadingHistory && messages.length === 1 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => send(suggestion)}
                  className="flex items-center gap-1.5 rounded-full border border-border bg-background px-4 py-2 text-xs text-muted transition hover:border-gold/50 hover:text-gold"
                >
                  <Sparkles className="h-3 w-3" strokeWidth={1.75} />
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-border bg-surface p-4">
          <div className="flex items-center gap-3">
            <input
              className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30 disabled:opacity-60"
              placeholder="Nhập câu hỏi của bạn..."
              value={input}
              disabled={loadingHistory}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && send(input)}
            />
            <button
              onClick={() => send(input)}
              disabled={sending || loadingHistory}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ink text-gold-soft transition hover:bg-ink-soft disabled:opacity-40"
              aria-label="Gửi"
            >
              <Send className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}

const SOURCE_LABELS: Record<Source["source_type"], string> = {
  bql_internal: "Tài liệu Ban quản lý",
  public_regulation: "Quy định pháp luật công khai",
  unofficial_web: "Trang tham khảo (chưa xác minh với BQL)",
  // Nói thẳng đây là dữ liệu mô phỏng. Trình bày số liệu tự dựng như thể là
  // số thật trước mặt doanh nghiệp là mất uy tín ngay khi có người biết rõ.
  synthetic_demo: "Quy trình mô phỏng (dữ liệu demo)",
};

function SourceCard({ source }: { source: Source }) {
  const Icon = source.source_type === "bql_internal" ? FileText : Scale;

  return (
    <div className="rounded-xl border border-border bg-background px-3.5 py-2.5">
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
        <div className="min-w-0">
          <p className="text-xs font-medium text-ink">{source.title}</p>
          <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted">
            {source.snippet}
          </p>
          <p className="mt-1 text-[10px] uppercase tracking-wider text-muted">
            {SOURCE_LABELS[source.source_type]}
          </p>
        </div>
      </div>
    </div>
  );
}
