"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, FileText, Loader2, Scale, Send, Sparkles } from "lucide-react";

import Layout from "../components/Layout";
import Button from "../components/Button";
import { api, describeError, type Source } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  sources?: Source[];
  refused?: boolean;
  time: string;
};

function now(): string {
  return new Date().toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const GREETING: Message = {
  id: 0,
  role: "assistant",
  text: "Xin chào 👋 Tôi là MoveInMate AI. Hỏi tôi bất kỳ thủ tục nào liên quan đến việc nhận nhà — mọi câu trả lời đều kèm nguồn tài liệu.",
  time: "",
};

const SUGGESTIONS = [
  "Làm thẻ xe cần giấy tờ gì?",
  "Hồ sơ làm thẻ cư dân gồm những gì?",
  "Đăng ký tạm trú thế nào?",
];

export default function ChatPage() {
  const { userId } = useDemoUser();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || sending) return;

    setMessages((prev) => [
      ...prev,
      { id: prev.length + 1, role: "user", text: question, time: now() },
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
          time: now(),
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
          time: now(),
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
          {messages.map((message) => (
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

                {message.time && (
                  <p
                    className={`mt-1 text-[11px] text-muted ${message.role === "user" ? "text-right" : ""}`}
                  >
                    {message.time}
                  </p>
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

          <div ref={bottomRef} />

          {messages.length === 1 && (
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
              className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
              placeholder="Nhập câu hỏi của bạn..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && send(input)}
            />
            <Button
              onClick={() => send(input)}
              disabled={sending}
              size="icon"
              className="rounded-xl"
              aria-label="Gửi"
            >
              <Send className="h-4 w-4" strokeWidth={1.75} />
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}

function SourceCard({ source }: { source: Source }) {
  const official = source.source_type === "bql_internal";
  const Icon = official ? FileText : Scale;

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
            {official ? "Tài liệu Ban quản lý" : "Quy định pháp luật công khai"}
          </p>
        </div>
      </div>
    </div>
  );
}
