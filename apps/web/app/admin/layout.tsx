import type { ReactNode } from "react";

import { BanksProvider } from "@/lib/mock/banks-store";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <BanksProvider>{children}</BanksProvider>;
}
