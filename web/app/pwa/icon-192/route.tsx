import { ImageResponse } from "next/og";

import { AppIconMark } from "../../pwa-icon";

const SIZE = 192;

export async function GET() {
  return new ImageResponse(AppIconMark(SIZE), { width: SIZE, height: SIZE });
}
