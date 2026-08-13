"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  Compass,
  FileText,
  Loader2,
  MessageSquarePlus,
  Scale,
  Send,
  Sparkles,
} from "lucide-react";

import Layout from "../components/Layout";
import {
  api,
  type ChatHistoryEntry,
  type ConversationSummary,
  type Source,
  type SuggestedAction,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  sources?: Source[];
  refused?: boolean;
  suggestedAction?: SuggestedAction | null;
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
 * gian tăng dần từ backend nên chỉ cần map tuần tự, không cần sort lại.
 * `suggestedAction` không có ở đây — `CHAT_HISTORY` chưa lưu field này (v1),
 * chỉ tin nhắn vừa gửi trong phiên hiện tại mới có nút điều hướng. */
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
  // `null` = hội thoại mới, chưa gửi câu nào — chỉ có giá trị sau khi backend
  // trả về `conversation_id` ở lần gửi đầu tiên.
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  // Chỉ bật khi đang MỞ một hội thoại cũ từ sidebar — khác với trước đây
  // (từng chặn cả trang lúc mới vào): hội thoại mới gõ được ngay, không phải
  // chờ gì cả.
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await api.getConversations(userId));
    } catch (err) {
      // Sidebar lỗi không được chặn khung chat chính — cư dân vẫn hỏi được
      // câu mới dù danh sách hội thoại cũ tải hỏng.
      console.error("[chat] không tải được danh sách hội thoại:", err);
    } finally {
      setLoadingConversations(false);
    }
  }, [userId]);

  useEffect(() => {
    if (ready) loadConversations();
  }, [ready, loadConversations]);

  const startNewConversation = () => {
    if (loadingMessages) return;
    setConversationId(null);
    setMessages([GREETING]);
    setInput("");
  };

  const openConversation = async (id: string) => {
    if (id === conversationId || loadingMessages) return;
    setLoadingMessages(true);
    try {
      const entries = await api.getConversationMessages(userId, id);
      setConversationId(id);
      setMessages(historyToMessages(entries));
    } catch (err) {
      console.error("[chat] không mở được hội thoại:", err);
    } finally {
      setLoadingMessages(false);
    }
  };

  const send = async (text: string) => {
    const question = text.trim();
    // `ready` false = chưa có danh tính, đang trên đường chuyển về /login.
    if (!question || sending || !ready || loadingMessages) return;

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
          suggestedAction: reply.suggested_action,
        },
      ]);
      // Lần gửi đầu của hội thoại mới: đây là lúc backend chính thức sinh ra
      // `conversation_id` — mọi câu hỏi sau đó trong phiên này gửi kèm id
      // này để AI hiểu ngữ cảnh (rewrite_query).
      setConversationId(reply.conversation_id);
      loadConversations(); // cập nhật preview/số lượt/thứ tự mới nhất ở sidebar
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
      <div className="flex h-[calc(100vh-9rem)] gap-4">
        <ConversationSidebar
          conversations={conversations}
          activeId={conversationId}
          loading={loadingConversations}
          onSelect={openConversation}
          onNew={startNewConversation}
        />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-surface">
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
            {loadingMessages && (
              <div className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang mở hội thoại...
              </div>
            )}

            {!loadingMessages && messages.map((message) => (
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

                  {message.suggestedAction && (
                    <SuggestedActionCard action={message.suggestedAction} />
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

            {!loadingMessages && messages.length === 1 && (
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
                disabled={loadingMessages}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && send(input)}
              />
              <button
                onClick={() => send(input)}
                disabled={sending || loadingMessages}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ink text-gold-soft transition hover:bg-ink-soft disabled:opacity-40"
                aria-label="Gửi"
              >
                <Send className="h-4 w-4" strokeWidth={1.75} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

/** Danh sách hội thoại đã lưu (US-07) — bấm vào để mở lại và hỏi tiếp có
 * ngữ cảnh (`rewrite_query` ở backend dùng vài lượt gần nhất của đúng hội
 * thoại đang mở). "Cuộc trò chuyện mới" không gọi API gì — chỉ dọn state,
 * hội thoại thật chỉ được tạo ở backend khi gửi câu hỏi đầu tiên. */
function ConversationSidebar({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <div className="flex w-64 shrink-0 flex-col overflow-hidden rounded-2xl border border-border bg-surface">
      <div className="border-b border-border p-3">
        <button
          onClick={onNew}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2.5 text-sm font-medium text-ink transition hover:border-gold/50 hover:text-gold"
        >
          <MessageSquarePlus className="h-4 w-4" strokeWidth={1.75} />
          Cuộc trò chuyện mới
        </button>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {loading && (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Đang tải...
          </div>
        )}

        {!loading && conversations.length === 0 && (
          <p className="px-3 py-4 text-center text-xs text-muted">
            Chưa có hội thoại nào đã lưu.
          </p>
        )}

        {!loading &&
          conversations.map((conv) => (
            <button
              key={conv.conversation_id}
              onClick={() => onSelect(conv.conversation_id)}
              className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${
                conv.conversation_id === activeId
                  ? "bg-ink text-white"
                  : "text-ink hover:bg-background"
              }`}
            >
              <p className="truncate">{conv.preview}</p>
              <p
                className={`mt-0.5 text-[11px] ${
                  conv.conversation_id === activeId ? "text-white/60" : "text-muted"
                }`}
              >
                {conv.message_count} lượt hỏi đáp
              </p>
            </button>
          ))}
      </div>
    </div>
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

/**
 * `checklist_item_id` null = backend không đối chiếu chắc chắn được mục nào
 * (xem docstring `SuggestedAction` phía backend) — khi đó chỉ hiện chữ, ẩn nút.
 */
function SuggestedActionCard({ action }: { action: SuggestedAction }) {
  return (
    <div className="mt-2 flex items-center justify-between gap-3 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-2.5">
      <div className="flex min-w-0 items-center gap-2">
        <Compass className="h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
        <p className="truncate text-xs text-ink">{action.procedure_name}</p>
      </div>
      {action.checklist_item_id !== null && (
        <Link
          href={`/checklist?item=${action.checklist_item_id}`}
          className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-[11px] font-medium text-white transition hover:bg-ink-soft"
        >
          Đến mục này
        </Link>
      )}
    </div>
  );
}

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
