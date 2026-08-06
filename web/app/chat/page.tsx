"use client";

import { useState } from "react";
import Layout from "../components/Layout";
import { Bot, Send, Sparkles } from "lucide-react";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

const initialMessages: Message[] = [
  {
    id: 1,
    role: "assistant",
    text: "Xin chào 👋 Tôi là MoveInMate AI. Tôi có thể hỗ trợ bạn mọi thủ tục liên quan đến bàn giao và nhận nhà.",
  },
  {
    id: 2,
    role: "user",
    text: "Tôi cần hỗ trợ thủ tục nhận nhà.",
  },
];

const suggestions = [
  "Hồ sơ cần chuẩn bị khi nhận nhà là gì?",
  "Quy trình đăng ký cư dân diễn ra thế nào?",
  "Tôi cần đóng những khoản phí nào?",
];

export default function ChatPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(initialMessages);

  const sendMessage = () => {
    if (!message.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: prev.length + 1, role: "user", text: message.trim() },
    ]);
    setMessage("");
  };

  return (
    <Layout>
      <div className="flex h-[calc(100vh-9rem)] flex-col overflow-hidden rounded-2xl border border-border bg-surface">
        {/* Conversation header */}
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

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-lg rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "rounded-br-sm bg-ink text-white"
                    : "rounded-bl-sm border border-border bg-background text-ink"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}

          {messages.length <= 2 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => setMessage(s)}
                  className="flex items-center gap-1.5 rounded-full border border-border bg-background px-4 py-2 text-xs text-muted transition hover:border-gold/50 hover:text-gold"
                >
                  <Sparkles className="h-3 w-3" strokeWidth={1.75} />
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border bg-surface p-4">
          <div className="flex items-center gap-3">
            <input
              className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
              placeholder="Nhập câu hỏi của bạn..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />

            <button
              onClick={sendMessage}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ink text-gold-soft transition hover:bg-ink-soft"
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
