"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  Car,
  ChevronRight,
  Compass,
  ExternalLink,
  FileText,
  IdCard,
  Image as ImageIcon,
  Loader2,
  MapPin,
  MessageSquarePlus,
  Paperclip,
  Scale,
  Send,
  ThumbsDown,
  ThumbsUp,
  Wallet,
  X,
} from "lucide-react";

import Layout from "../components/Layout";
import ChatContextPanel from "../components/ChatContextPanel";
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

// 4 nhóm câu hỏi hay gặp nhất, mỗi nhóm neo vào tài liệu KB đã kiểm chứng
// (data/kb/web/) — tránh chọn câu hỏi ngoài phạm vi tài liệu để không vô tình
// demo đúng vào chỗ guard chống bịa còn yếu (xem PROJECT_CHARTER.md mục 7).
const SUGGESTIONS = [
  { icon: IdCard, text: "Hồ sơ làm thẻ cư dân gồm những gì?" },
  { icon: Car, text: "Làm thẻ xe cần giấy tờ gì?" },
  { icon: MapPin, text: "Đăng ký tạm trú thế nào?" },
  { icon: Wallet, text: "Phí dịch vụ chung cư tính thế nào?" },
];

/** Mỗi lượt hỏi đáp đã lưu tách thành 2 bong bóng (hỏi + đáp) để dùng chung
 * cách render với tin nhắn trong phiên hiện tại. `entries` đã sắp theo thời
 * gian tăng dần từ backend nên chỉ cần map tuần tự, không cần sort lại.
 * `suggestedAction` không có ở đây — `CHAT_HISTORY` chưa lưu field này (v1),
 * chỉ tin nhắn trong phiên hiện tại mới có nút điều hướng. */
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
  // Chỉ 1 nguồn được xem chi tiết tại một thời điểm — modal dùng chung cho
  // mọi chip trong mọi bong bóng, không cần state riêng theo từng chip.
  const [openSource, setOpenSource] = useState<Source | null>(null);

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
      <div className="flex gap-4">
        <ConversationSidebar
          conversations={conversations}
          activeId={conversationId}
          loading={loadingConversations}
          onSelect={openConversation}
          onNew={startNewConversation}
        />

        <div className="flex h-[calc(100vh-9rem)] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-surface">
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

            {!loadingMessages && messages.length === 1 && (
              <div className="rounded-2xl border border-border bg-background px-6 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink">
                    <Bot className="h-5 w-5 text-gold-soft" strokeWidth={1.75} />
                  </div>
                  <div>
                    <p className="flex items-center gap-2 font-display text-sm font-semibold text-ink">
                      MoveInMate AI
                      <span className="flex items-center gap-1 rounded-full bg-emerald/10 px-2 py-0.5 text-[10px] font-medium text-emerald">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
                        Online
                      </span>
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-muted">
                      {GREETING.text}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {!loadingMessages && messages.length > 1 && messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="max-w-lg">
                  <div
                    className={`rounded-2xl px-5 py-3.5 ${
                      message.role === "user"
                        ? "rounded-br-sm bg-ink text-white"
                        : message.refused
                          ? "rounded-bl-sm border border-gold/40 bg-gold-tint text-ink"
                          : "rounded-bl-sm border border-border bg-background text-ink"
                    }`}
                  >
                    {/* Câu trả lời chính — phải nhận ra được trong <1 giây, nên
                        đậm và lớn hơn hẳn phần nguồn bên dưới. */}
                    <p
                      className={`text-[13.5px] font-normal leading-relaxed ${
                        message.role === "user" ? "text-white" : "text-ink"
                      }`}
                    >
                      {message.text}
                    </p>

                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2.5 border-t border-dashed border-border pt-2.5">
                        <div className="flex flex-wrap gap-1.5">
                          {message.sources.map((source) => (
                            <SourceChip
                              key={source.document_id}
                              source={source}
                              onOpen={() => setOpenSource(source)}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {message.suggestedAction && (
                    <SuggestedActionCard action={message.suggestedAction} />
                  )}

                  {message.role === "assistant" && (
                    <FeedbackButtons userId={userId} messageId={message.id} />
                  )}

                  {/* Guard chống bịa từ chối trả lời (answer_source: no_context)
                      — thay vì để người dùng tự nghĩ câu hỏi khác, gợi ý luôn
                      các chủ đề đã có tài liệu kiểm chứng. Tái dùng nguyên
                      SUGGESTIONS đã dùng ở màn hình chào, không phải danh sách
                      mới — chỉ dẫn về "hỏi gì khác", CHƯA dẫn vào luồng hành
                      động (form đăng ký...) vì luồng đó chưa tồn tại ở backend. */}
                  {message.role === "assistant" && message.refused && (
                    <div className="mt-2.5">
                      <p className="text-[11px] text-muted">Bạn có thể hỏi thử:</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {SUGGESTIONS.map(({ icon: Icon, text }) => (
                          <button
                            key={text}
                            onClick={() => send(text)}
                            className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-[11px] text-ink/70 transition hover:border-gold/50 hover:text-gold"
                          >
                            <Icon className="h-3 w-3 shrink-0 text-gold" strokeWidth={1.75} />
                            {text}
                          </button>
                        ))}
                      </div>
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

            {!loadingMessages && messages.length === 1 && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                {SUGGESTIONS.map(({ icon: Icon, text }) => (
                  <button
                    key={text}
                    onClick={() => send(text)}
                    className="flex items-center gap-2 rounded-xl border border-border bg-background px-3.5 py-2.5 text-left text-xs text-ink/80 transition hover:border-gold/50 hover:text-gold"
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
                    {text}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-border bg-surface p-4">
            <div className="flex items-center gap-2">
              <button
                disabled
                title="Sắp có — chưa nối API tải lên giấy tờ"
                aria-label="Đính kèm tệp (sắp có)"
                className="flex h-11 w-11 shrink-0 cursor-not-allowed items-center justify-center rounded-xl text-muted/50"
              >
                <Paperclip className="h-4 w-4" strokeWidth={1.75} />
              </button>
              <button
                disabled
                title="Sắp có — chưa nối API tải ảnh giấy tờ (CCCD, thẻ xe...)"
                aria-label="Tải ảnh (sắp có)"
                className="flex h-11 w-11 shrink-0 cursor-not-allowed items-center justify-center rounded-xl text-muted/50"
              >
                <ImageIcon className="h-4 w-4" strokeWidth={1.75} />
              </button>
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

        <ChatContextPanel userId={userId} ready={ready} />
      </div>

      {openSource && (
        <SourceModal source={openSource} onClose={() => setOpenSource(null)} />
      )}
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

type Rating = "up" | "down";

/**
 * V7 — chưa có cột lưu rating ở `chat_history` và `POST /chat` cũng chưa trả
 * `chat_id` cho tin nhắn vừa gửi (chỉ tin nhắn tải từ lịch sử mới có id thật),
 * nên chưa thể đồng bộ lên backend. Lưu tạm ở localStorage theo máy — còn hơn
 * mất trắng mỗi lần F5, nhưng KHÔNG giả vờ đã lưu vào hệ thống (xem dòng chú
 * thích trong `FeedbackButtons`). Cần Hiếu thêm cột + endpoint để làm tiếp.
 */
function feedbackKey(userId: number, messageId: number): string {
  return `moveinmate.chat-feedback.${userId}.${messageId}`;
}

function readFeedback(userId: number, messageId: number): Rating | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(feedbackKey(userId, messageId));
  return raw === "up" || raw === "down" ? raw : null;
}

function FeedbackButtons({ userId, messageId }: { userId: number; messageId: number }) {
  const [rating, setRating] = useState<Rating | null>(() => readFeedback(userId, messageId));

  const rate = (value: Rating) => {
    const next = rating === value ? null : value;
    setRating(next);
    if (next) {
      window.localStorage.setItem(feedbackKey(userId, messageId), next);
    } else {
      window.localStorage.removeItem(feedbackKey(userId, messageId));
    }
  };

  return (
    <div className="mt-1.5 flex items-center gap-2.5">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => rate("up")}
          aria-label="Câu trả lời hữu ích"
          aria-pressed={rating === "up"}
          className={`flex h-6 w-6 items-center justify-center rounded-md transition ${
            rating === "up" ? "bg-emerald/15 text-emerald" : "text-muted hover:bg-ink/[0.06] hover:text-ink"
          }`}
        >
          <ThumbsUp className="h-3.5 w-3.5" strokeWidth={1.75} />
        </button>
        <button
          type="button"
          onClick={() => rate("down")}
          aria-label="Câu trả lời chưa hữu ích"
          aria-pressed={rating === "down"}
          className={`flex h-6 w-6 items-center justify-center rounded-md transition ${
            rating === "down" ? "bg-danger/15 text-danger" : "text-muted hover:bg-ink/[0.06] hover:text-ink"
          }`}
        >
          <ThumbsDown className="h-3.5 w-3.5" strokeWidth={1.75} />
        </button>
      </div>
      {rating && (
        <span className="text-[10px] text-muted/70">Đã ghi nhận trên trình duyệt này</span>
      )}
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

/** Nhãn ngắn cho chip — bản đầy đủ (`SOURCE_LABELS`) chỉ hiện khi mở rộng. */
const SOURCE_LABELS_SHORT: Record<Source["source_type"], string> = {
  bql_internal: "BQL",
  public_regulation: "Pháp luật",
  unofficial_web: "Chưa xác minh",
  synthetic_demo: "Demo",
};

/**
 * Mỗi nguồn là 1 chip 1 dòng. Bấm chip mở modal chi tiết (`SourceModal`)
 * thay vì mở rộng tại chỗ — chip không giữ state riêng nữa, chỉ báo lên
 * `onOpen` của component cha (`ChatPage`), nơi quản lý "đang xem nguồn nào".
 */
function SourceChip({ source, onOpen }: { source: Source; onOpen: () => void }) {
  const Icon = source.source_type === "bql_internal" ? FileText : Scale;

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-haspopup="dialog"
      className="flex min-w-0 max-w-full items-center gap-1.5 rounded-lg bg-ink/[0.04] px-2.5 py-1.5 text-[12px] text-muted transition hover:bg-ink/[0.08]"
    >
      <Icon className="h-3 w-3 shrink-0 text-gold" strokeWidth={1.75} />
      <span className="min-w-0 max-w-[10rem] truncate text-ink/80">{source.title}</span>
      <span className="shrink-0 rounded-full bg-ink/[0.06] px-1.5 py-0.5 text-[10px] text-muted">
        {SOURCE_LABELS_SHORT[source.source_type]}
      </span>
      <ChevronRight className="h-3 w-3 shrink-0 text-muted" strokeWidth={2} />
    </button>
  );
}

/**
 * Modal chi tiết nguồn — overlay tối phía sau (bấm ra ngoài để đóng) + panel
 * fade/scale-in. `visible` trễ 1 khung hình sau khi mount để trigger CSS
 * transition (mount thẳng ở trạng thái cuối thì trình duyệt không animate).
 *
 * "Xem văn bản gốc" khoá và chú thích rõ lý do — Source hiện chưa có field
 * link file (`src/models/schemas.py` chỉ có document_id/title/snippet/
 * source_type), nên không giả một đường link không trỏ đi đâu cả.
 */
function SourceModal({ source, onClose }: { source: Source; onClose: () => void }) {
  const [visible, setVisible] = useState(false);
  const Icon = source.source_type === "bql_internal" ? FileText : Scale;

  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className={`absolute inset-0 bg-black/45 transition-opacity duration-200 ${
          visible ? "opacity-100" : "opacity-0"
        }`}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={source.title}
        onClick={(event) => event.stopPropagation()}
        className={`relative w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl transition-all duration-200 ${
          visible ? "scale-100 opacity-100" : "scale-95 opacity-0"
        }`}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng"
          className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-ink/[0.06] hover:text-ink"
        >
          <X className="h-4 w-4" strokeWidth={1.75} />
        </button>

        <div className="flex items-start gap-3 pr-8">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gold-tint">
            <Icon className="h-4 w-4 text-gold" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <p className="font-display text-sm font-semibold leading-snug text-ink">
              {source.title}
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-wider text-muted">
              {SOURCE_LABELS[source.source_type]}
            </p>
          </div>
        </div>

        <div className="mt-4 max-h-64 overflow-y-auto rounded-xl border border-border bg-background px-4 py-3.5">
          <p className="text-[13px] leading-relaxed text-ink/85">{source.snippet}</p>
        </div>

        <button
          type="button"
          disabled
          title="Sắp có — backend chưa trả link/file văn bản gốc cho từng nguồn"
          className="mt-4 flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-xl border border-border px-4 py-2.5 text-xs font-medium text-muted/60"
        >
          <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.75} />
          Xem văn bản gốc — Sắp có
        </button>
      </div>
    </div>
  );
}
