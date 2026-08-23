"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Bot,
  Car,
  ChevronRight,
  Compass,
  ExternalLink,
  FileText,
  HelpCircle,
  IdCard,
  ListChecks,
  Loader2,
  MapPin,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Scale,
  Send,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";

import Layout from "../components/Layout";
import ChatContextPanel from "../components/ChatContextPanel";
import AttachmentUploader from "../components/AttachmentUploader";
import SubmitApplicationDialog from "../components/SubmitApplicationDialog";
import FormReviewDialog from "../components/FormReviewDialog";
import { SELF_DECLARED_DOCUMENT } from "../../lib/applicationForms";
import {
  api,
  type Application,
  type ChatHistoryEntry,
  type Checklist,
  type ChecklistItem,
  type ConversationSummary,
  type Profile,
  type ProcedureOption,
  type Source,
  type SuggestedAction,
  type ApplicationFormData,
  type ChatFormState,
  type FormSchema,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { linkifyText } from "../../lib/linkify";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  sources?: Source[];
  refused?: boolean;
  suggestedAction?: SuggestedAction | null;
  procedureOptions?: ProcedureOption[];
};

type PendingFormReview = {
  checklistItemId: number;
  itemName: string;
  schema: FormSchema;
  initialData: ApplicationFormData;
};

type ActiveFormFlow = PendingFormReview & ChatFormState;

const GREETING: Message = {
  id: 0,
  role: "assistant",
  text: "Xin chào 👋 Tôi là Trợ lý MoveInMate. Tôi có thể giúp bạn hiểu thủ tục, chuẩn bị giấy tờ và tìm đúng nơi cần nộp.",
};

const CONTINUE_QUESTION = "Tôi còn thiếu giấy tờ gì?";

// 5 nhóm câu hỏi hay gặp nhất — khớp 5 ý "Tôi cần làm đơn gì / chuẩn bị giấy
// tờ gì / kiểm tra hồ sơ / giải thích giấy tờ / hướng dẫn nộp đơn" trong đề
// xuất, nhưng viết lại thành câu hỏi THẬT thay vì nhãn mục — mỗi câu neo vào
// đúng tài liệu KB đã kiểm chứng (data/kb/bql/, data/kb/web/), tránh chọn câu
// ngoài phạm vi tài liệu để không vô tình demo vào chỗ guard chống bịa còn
// yếu (xem PROJECT_CHARTER.md mục 7).
const SUGGESTIONS = [
  { icon: ListChecks, text: "Khi mới nhận nhà tôi cần làm những thủ tục gì?" },
  { icon: IdCard, text: "Làm thẻ cư dân cần chuẩn bị giấy tờ gì?" },
  { icon: HelpCircle, text: CONTINUE_QUESTION },
  { icon: MapPin, text: "Đăng ký tạm trú cần hồ sơ gì?" },
  { icon: HelpCircle, text: "Thẻ cư dân dùng để làm gì?" },
  { icon: Car, text: "Nộp hồ sơ đăng ký thẻ xe ở đâu, mất bao lâu?" },
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

function buildContinueMessage(checklist: Checklist, applications: Application[]): Message {
  const openApplications = applications
    .filter((application) => !["approved", "delivered"].includes(application.status))
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    );
  const latest = openApplications[0];
  const item = latest
    ? checklist.items.find((candidate) => candidate.id === latest.checklist_item_id)
    : checklist.items.find((candidate) => !candidate.completed);

  if (!item) {
    return {
      id: 1,
      role: "assistant",
      text: `Bạn đã hoàn thành ${checklist.overall.completed}/${checklist.overall.total} việc trong hành trình nhận nhà. Hiện không còn việc nào đang chờ bạn xử lý. Nếu cần kiểm tra lại thủ tục hoặc quy định, bạn cứ hỏi tôi.`,
    };
  }

  const uploadedTypes = new Set(
    (latest?.attachments ?? [])
      .map((attachment) => attachment.document_type)
      .filter((value): value is NonNullable<typeof value> => Boolean(value)),
  );
  const inferredMissing = item.required_documents.filter(
    (document) => !uploadedTypes.has(document.code),
  );
  const missingDocuments = latest
    ? latest.missing_documents === null
      ? []
      : latest.missing_documents ?? inferredMissing
    : item.required_documents;
  const lines = [
    `Bạn đang làm ${item.task_name}.`,
    latest
      ? latest.status === "needs_info" || latest.status === "rejected"
        ? "Hồ sơ đang cần bạn bổ sung giấy tờ."
        : "Hồ sơ hiện đang được xử lý."
      : "Bạn chưa nộp hồ sơ. Mình có thể giúp bạn bắt đầu ngay tại đây.",
  ];

  if (latest?.bql_note) lines.push(`BQL nhắn: ${latest.bql_note}`);
  if (latest?.missing_documents === null || latest?.unlabelled_count) {
    lines.push(
      `Bạn có ${latest.unlabelled_count ?? latest.attachments.filter((attachment) => !attachment.document_type).length} tệp chưa được phân loại; cần kiểm tra lại trước khi kết luận còn thiếu giấy tờ nào.`,
    );
  } else if (missingDocuments.length > 0) {
    lines.push(`Giấy tờ còn cần chuẩn bị: ${missingDocuments.map((document) => document.label).join(", ")}.`);
  } else if (item.required_documents.length > 0 && latest?.attachments.length) {
    lines.push("Các loại giấy tờ bắt buộc đã được tải lên; bạn nên kiểm tra lại phản hồi của BQL trước khi tiếp tục.");
  }
  lines.push(
    latest
      ? "Bạn có thể bổ sung giấy tờ ngay bên dưới."
      : "Bấm “Nộp hồ sơ tại đây” để tiếp tục.",
  );

  return {
    id: 1,
    role: "assistant",
    text: lines.join("\n\n"),
    suggestedAction: {
      type: "navigate_to_submission",
      procedure_name: item.task_name,
      checklist_item_id: item.id,
    },
  };
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageContent />
    </Suspense>
  );
}

// `useSearchParams()` bắt buộc nằm trong <Suspense> — đọc `?q=` để điền sẵn
// câu hỏi khi có nơi khác (vd dialog "Ký nội quy") trỏ sang đây.
function ChatPageContent() {
  const { userId, ready } = useDemoUser();
  const searchParams = useSearchParams();
  const [input, setInput] = useState(() => searchParams.get("q") ?? "");
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
  const [profile, setProfile] = useState<Profile | null>(null);
  const [formReview, setFormReview] = useState<PendingFormReview | null>(null);
  const [activeForm, setActiveForm] = useState<ActiveFormFlow | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const continuedRef = useRef(false);

  useEffect(() => {
    setHistoryOpen(window.localStorage.getItem("moveinmate.chat-history-open") !== "0");
  }, []);

  const setHistoryVisibility = (open: boolean) => {
    setHistoryOpen(open);
    window.localStorage.setItem("moveinmate.chat-history-open", open ? "1" : "0");
  };

  useEffect(() => {
    // `scrollIntoView` cuộn tất cả ancestor có thể cuộn, gồm cả khung trang
    // trong Layout. Khi lịch sử chat dài, nó kéo toàn bộ page xuống sâu và
    // để lại một vùng trắng lớn. Chỉ cuộn đúng danh sách tin nhắn.
    const container = messagesContainerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

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
    if (ready) {
      loadConversations();
      api.getProfile(userId).then(setProfile).catch(() => setProfile(null));
    }
  }, [ready, loadConversations, userId]);

  useEffect(() => {
    if (!ready || searchParams.get("continue") !== "1" || continuedRef.current) return;
    continuedRef.current = true;
    setLoadingMessages(true);
    Promise.all([api.getChecklist(userId), api.getApplications(userId)])
      .then(([tasks, residentApplications]) => {
        setMessages([GREETING, buildContinueMessage(tasks, residentApplications)]);
      })
      .catch(() => {
        setMessages([
          GREETING,
          {
            id: 1,
            role: "assistant",
            text: "Tôi chưa tải được tiến độ của bạn lúc này. Bạn có thể mở Việc cần làm để tiếp tục, hoặc thử lại sau ít phút.",
            refused: true,
          },
        ]);
      })
      .finally(() => setLoadingMessages(false));
  }, [ready, searchParams, userId]);

  const startNewConversation = () => {
    if (loadingMessages) return;
    setConversationId(null);
    setMessages([GREETING]);
    setInput("");
    setFormReview(null);
    setActiveForm(null);
  };

  const openConversation = async (id: string) => {
    if (id === conversationId || loadingMessages) return;
    setActiveForm(null);
    setFormReview(null);
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

    if (question === CONTINUE_QUESTION) {
      try {
        const [tasks, residentApplications] = await Promise.all([
          api.getChecklist(userId),
          api.getApplications(userId),
        ]);
        setMessages((prev) => [
          ...prev,
          { ...buildContinueMessage(tasks, residentApplications), id: prev.length + 1 },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { id: prev.length + 1, role: "assistant", text: "Mình chưa kiểm tra được hồ sơ lúc này. Bạn thử lại sau ít phút nhé.", refused: true },
        ]);
      } finally {
        setSending(false);
      }
      return;
    }

    try {
      const reply = await api.sendChat(
        userId,
        question,
        conversationId ?? undefined,
        activeForm
          ? {
              checklist_item_id: activeForm.checklist_item_id,
              form_data: activeForm.form_data,
            }
          : undefined,
      );
      const selectedProcedure = messages
        .flatMap((message) => message.procedureOptions ?? [])
        .find((option) => option.task_name === question);
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          text: reply.answer,
          sources: reply.sources,
          refused:
            (reply.intent == null || reply.intent === "qa") &&
            reply.answer_source === "no_context",
          suggestedAction: reply.suggested_action,
          procedureOptions:
            reply.intent === "disambiguation" ? reply.options ?? [] : undefined,
        },
      ]);
      if (
        (reply.intent === "form_generation" || reply.intent === "form_review") &&
        reply.checklist_item_id != null &&
        reply.form_schema
      ) {
        let itemName = selectedProcedure?.task_name ?? activeForm?.itemName;
        if (!itemName) {
          try {
            const checklist = await api.getChecklist(userId);
            itemName = checklist.items.find(
              (item) => item.id === reply.checklist_item_id,
            )?.task_name;
          } catch {
            // Tên chỉ là nhãn hiển thị; lỗi tải checklist không được làm mất
            // state của luồng form đang diễn ra.
          }
        }
        const nextForm: ActiveFormFlow = {
          checklistItemId: reply.checklist_item_id,
          checklist_item_id: reply.checklist_item_id,
          itemName: itemName ?? "Hồ sơ thủ tục",
          schema: reply.form_schema,
          initialData: reply.form_data ?? {},
          form_data: reply.form_data ?? {},
        };
        setActiveForm(nextForm);
        setFormReview(reply.intent === "form_review" ? nextForm : null);
      } else if (reply.intent === "disambiguation" || reply.intent === "qa") {
        setActiveForm(null);
        setFormReview(null);
      }
      // Lần gửi đầu của hội thoại mới: đây là lúc backend chính thức sinh ra
      // `conversation_id` — mọi câu hỏi sau đó trong phiên này gửi kèm id
      // này để AI hiểu ngữ cảnh (rewrite_query).
      if (reply.conversation_id) setConversationId(reply.conversation_id);
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
    <Layout wide>
      <div className="flex gap-5">
        <div className="hidden shrink-0 2xl:flex">
          {historyOpen ? (
            <ConversationSidebar
              conversations={conversations}
              activeId={conversationId}
              loading={loadingConversations}
              onSelect={openConversation}
              onNew={startNewConversation}
              onCollapse={() => setHistoryVisibility(false)}
            />
          ) : (
            <button type="button" onClick={() => setHistoryVisibility(true)} title="Mở lịch sử chat" aria-label="Mở lịch sử chat" className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-white text-muted shadow-sm hover:border-blue-300 hover:text-blue-600">
              <PanelLeftOpen className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="flex h-[calc(100dvh-13rem)] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/90 bg-surface/95 shadow-[0_22px_52px_-34px_rgba(0,45,98,0.55)] ring-1 ring-border/50 lg:h-[calc(100vh-9rem)]">
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-ink to-[#075985] shadow-md">
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

          <div ref={messagesContainerRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6">
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
                      Chào {profile?.full_name ?? "bạn"} 👋 Mình là Trợ lý MoveInMate. Mình có thể giúp bạn hoàn thành thủ tục nhận nhà, kiểm tra giấy tờ còn thiếu và hướng dẫn từng bước.
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
                <div className="max-w-[min(46rem,88%)]">
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
                      className={`whitespace-pre-line text-[13.5px] font-normal leading-relaxed ${
                        message.role === "user" ? "text-white" : "text-ink"
                      }`}
                    >
                      {linkifyText(message.text)}
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

                    {message.procedureOptions && message.procedureOptions.length > 0 && (
                      <div className="mt-3 grid gap-2 border-t border-dashed border-border pt-3">
                        {message.procedureOptions.map((option, index) => (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() => send(option.task_name)}
                            disabled={sending || loadingMessages}
                            className="flex items-center justify-between rounded-xl border border-gold/40 bg-surface px-3.5 py-2.5 text-left text-xs font-medium text-ink transition hover:border-gold hover:text-gold disabled:opacity-50"
                          >
                            <span>{index + 1}. {option.task_name}</span>
                            <ChevronRight className="h-3.5 w-3.5 shrink-0" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {message.suggestedAction && (
                    <ChatSubmissionCard
                      action={message.suggestedAction}
                      userId={userId}
                      ready={ready}
                    />
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
                            className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-[11px] text-ink/85 transition hover:border-gold/50 hover:text-gold"
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
              <div className="pt-1">
                <p className="mb-2.5 text-sm font-semibold text-ink">Bạn muốn làm gì hôm nay?</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map(({ icon: Icon, text }) => (
                  <button
                    key={text}
                    onClick={() => send(text)}
                    className="flex items-center gap-2 rounded-xl border border-border bg-background px-3.5 py-2.5 text-left text-xs text-ink/90 transition hover:border-gold/50 hover:text-gold"
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
                    {text}
                  </button>
                ))}
                </div>
              </div>
            )}

          </div>

          <div className="border-t border-border bg-gradient-to-r from-white via-blue-50/25 to-cyan-50/25 p-4">
            {/* Gõ tới đâu khớp gợi ý tới đó — chỉ so trong 4 câu đã neo vào
                tài liệu KB kiểm chứng (SUGGESTIONS), không tự bịa câu mới,
                giữ đúng nguyên tắc không demo vào chỗ guard chống bịa còn yếu. */}
            {input.trim().length > 0 &&
              (() => {
                const query = input.trim().toLowerCase();
                const matches = SUGGESTIONS.filter(({ text }) =>
                  text.toLowerCase().includes(query),
                );
                if (matches.length === 0) return null;
                return (
                  <div className="mb-2.5 flex flex-wrap gap-1.5">
                    {matches.map(({ icon: Icon, text }) => (
                      <button
                        key={text}
                        onClick={() => send(text)}
                        disabled={sending || loadingMessages}
                        className="flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold-tint px-3 py-1.5 text-[11px] text-ink transition hover:border-gold disabled:opacity-50"
                      >
                        <Icon className="h-3 w-3 shrink-0 text-gold" strokeWidth={1.75} />
                        {text}
                      </button>
                    ))}
                  </div>
                );
              })()}

            <div className="flex items-center gap-2">
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
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-gold to-gold-soft text-white shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg disabled:transform-none disabled:opacity-40"
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
      {formReview && (
        <FormReviewDialog
          schema={formReview.schema}
          initialData={formReview.initialData}
          itemName={formReview.itemName}
          userId={userId}
          checklistItemId={formReview.checklistItemId}
          onBack={() => setFormReview(null)}
          onSubmitted={() => {
            setFormReview(null);
            setActiveForm(null);
            setMessages((prev) => [
              ...prev,
              {
                id: prev.length + 1,
                role: "assistant",
                text: "Hồ sơ đã được gửi đến Ban quản lý. Bạn có thể theo dõi tiến độ ở mục Việc cần làm.",
              },
            ]);
          }}
        />
      )}
    </Layout>
  );
}

/** Danh sách hội thoại đã lưu (US-07) — bấm vào để mở lại và hỏi tiếp có
 * ngữ cảnh (`rewrite_query` ở backend dùng vài lượt gần nhất của đúng hội
 * thoại đang mở). "Đặt câu hỏi mới" không gọi API gì — chỉ dọn state,
 * hội thoại thật chỉ được tạo ở backend khi gửi câu hỏi đầu tiên. */
function ConversationSidebar({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onCollapse,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onCollapse: () => void;
}) {
  return (
    <div className="flex w-72 shrink-0 flex-col overflow-hidden rounded-2xl border border-white/90 bg-surface/95 shadow-soft ring-1 ring-border/50">
      <div className="border-b border-border p-3">
        <div className="flex items-center gap-2">
          <button onClick={onNew} className="flex min-w-0 flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2.5 text-sm font-medium text-ink transition hover:border-gold/50 hover:text-gold"><MessageSquarePlus className="h-4 w-4" strokeWidth={1.75} />Câu hỏi mới</button>
          <button type="button" onClick={onCollapse} title="Đóng lịch sử chat" aria-label="Đóng lịch sử chat" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border text-muted hover:text-blue-600"><PanelLeftClose className="h-4 w-4" /></button>
        </div>
        <p className="mt-3 px-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">Lịch sử hỗ trợ</p>
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
              <p className="line-clamp-2 leading-5">{conv.preview}</p>
              <p
                className={`mt-0.5 text-[11px] ${
                  conv.conversation_id === activeId ? "text-white/75" : "text-muted"
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
            rating === "up"
              ? "bg-emerald text-white shadow-sm"
              : "text-muted hover:bg-ink/[0.06] hover:text-ink"
          }`}
        >
          <ThumbsUp className="h-3.5 w-3.5" strokeWidth={rating === "up" ? 2.25 : 1.75} />
        </button>
        <button
          type="button"
          onClick={() => rate("down")}
          aria-label="Câu trả lời chưa hữu ích"
          aria-pressed={rating === "down"}
          className={`flex h-6 w-6 items-center justify-center rounded-md transition ${
            rating === "down"
              ? "bg-danger text-white shadow-sm"
              : "text-muted hover:bg-ink/[0.06] hover:text-ink"
          }`}
        >
          <ThumbsDown className="h-3.5 w-3.5" strokeWidth={rating === "down" ? 2.25 : 1.75} />
        </button>
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
function ChatSubmissionCard({
  action,
  userId,
  ready,
}: {
  action: SuggestedAction;
  userId: number;
  ready: boolean;
}) {
  const [item, setItem] = useState<ChecklistItem | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(action.checklist_item_id !== null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!ready || action.checklist_item_id === null) return;
    setLoading(true);
    try {
      const [checklist, applications] = await Promise.all([
        api.getChecklist(userId),
        api.getApplications(userId),
      ]);
      setItem(
        checklist.items.find((candidate) => candidate.id === action.checklist_item_id) ?? null,
      );
      setApplication(
        applications.find(
          (candidate) => candidate.checklist_item_id === action.checklist_item_id,
        ) ?? null,
      );
    } catch {
      setItem(null);
      setApplication(null);
    } finally {
      setLoading(false);
    }
  }, [action.checklist_item_id, ready, userId]);

  useEffect(() => {
    load();
  }, [load]);

  const requiredDocuments = item
    ? item.item_type === "bql_actionable"
      ? item.required_documents
      : [SELF_DECLARED_DOCUMENT]
    : [];

  return (
    <div className="mt-2 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-3">
      <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2">
        <Compass className="h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
        <p className="truncate text-xs text-ink">{action.procedure_name}</p>
      </div>
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-gold" />}
      {!loading && item && !application && (
        <button
          onClick={() => setSubmitting(true)}
          className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-[11px] font-medium text-white transition hover:bg-ink-soft"
        >
          Nộp hồ sơ tại đây
        </button>
      )}
      {!loading && action.checklist_item_id !== null && !item && (
        <Link
          href={`/checklist?item=${action.checklist_item_id}`}
          className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-[11px] font-medium text-white transition hover:bg-ink-soft"
        >
          Đến mục này
        </Link>
      )}
      </div>

      {!loading && item && application && (
        <div className="mt-3 border-t border-gold/25 pt-2">
          <p className="text-[11px] font-medium text-ink">
            Bổ sung giấy tờ ngay trong Trợ lý AI
          </p>
          <AttachmentUploader
            userId={userId}
            applicationId={application.application_id}
            attachments={application.attachments}
            required={application.kind === "self_declared"}
            requiredDocuments={requiredDocuments}
            onUploaded={(attachment) =>
              setApplication((current) =>
                current
                  ? { ...current, attachments: [...current.attachments, attachment] }
                  : current,
              )
            }
          />
        </div>
      )}

      {submitting && item && (
        <SubmitApplicationDialog
          userId={userId}
          item={item}
          onClose={() => setSubmitting(false)}
          onSubmitted={() => {
            setSubmitting(false);
            load();
          }}
        />
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
      <span className="min-w-0 max-w-[10rem] truncate text-ink/90">{source.title}</span>
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
        className={`relative w-full max-w-md rounded-2xl border border-border bg-surface shadow-soft p-6 shadow-2xl transition-all duration-200 ${
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

        <div className="mt-4 max-h-72 overflow-y-auto rounded-xl border border-border bg-background px-4 py-3.5">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">Đoạn trích liên quan</p>
          <SourceSnippet text={source.snippet} />
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

/** Backend nén whitespace của snippet thành một dòng. Khôi phục các ý có
 * dấu gạch đầu dòng để modal nguồn không biến danh sách giấy tờ thành một
 * đoạn văn khó đọc. Dấu … cuối chuỗi vẫn phản ánh giới hạn snippet backend. */
function SourceSnippet({ text }: { text: string }) {
  const normalized = text.trim();
  const parts = normalized
    .replace(/^[-–—]\s*/, "")
    .split(/\s+[-–—]\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length <= 1) {
    return <p className="whitespace-pre-line text-[13px] leading-6 text-ink/90">{normalized}</p>;
  }

  return (
    <ul className="space-y-2 text-[13px] leading-6 text-ink/90">
      {parts.map((part, index) => (
        <li key={`${index}-${part.slice(0, 16)}`} className="flex items-start gap-2">
          <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
          <span>{part}</span>
        </li>
      ))}
    </ul>
  );
}
