import {
  Bot,
  ClipboardList,
  Inbox,
  LayoutDashboard,
  Users,
  UserRound,
  FileText,
  type LucideIcon,
} from "lucide-react";

/**
 * Nguồn DUY NHẤT của menu điều hướng. Sidebar (desktop) và MobileTabBar
 * (mobile) cùng đọc từ đây.
 *
 * Nếu mỗi bên tự giữ một bản danh sách, sớm muộn chúng lệch nhau — đúng cái
 * bẫy REQUIRED_DOCUMENTS vừa dẹp xong hồi 18/08.
 */
export type NavItem = { title: string; icon: LucideIcon; href: string };

export const RESIDENT_NAV: NavItem[] = [
  { title: "Trang chủ", icon: LayoutDashboard, href: "/dashboard" },
  { title: "Trợ lý AI", icon: Bot, href: "/chat" },
  { title: "Việc cần làm", icon: ClipboardList, href: "/checklist" },
  { title: "Hồ sơ", icon: UserRound, href: "/profile" },
];

export const BQL_NAV: NavItem[] = [
  { title: "Tổng quan", icon: LayoutDashboard, href: "/bql/dashboard" },
  { title: "Yêu cầu", icon: Inbox, href: "/bql/applications" },
  { title: "Cư dân", icon: Users, href: "/bql/residents" },
  { title: "Tài liệu", icon: FileText, href: "/bql/documents" },
];
