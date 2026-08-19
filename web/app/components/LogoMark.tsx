import Image from "next/image";

/** Ô logo dùng chung — sidebar, màn đăng nhập. Đổi logo chỉ cần thay `public/logo-mark.png`. */
export default function LogoMark({
  size = 44,
  rounded = "rounded-lg",
  border = "border-border",
  className = "",
}: {
  size?: number;
  rounded?: string;
  border?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center border bg-white ${rounded} ${border} ${className}`}
      style={{ width: size, height: size }}
    >
      <Image
        src="/logo-mark.png"
        alt="MoveInMate"
        width={size}
        height={size}
        style={{ width: "88%", height: "88%", objectFit: "contain" }}
      />
    </div>
  );
}
