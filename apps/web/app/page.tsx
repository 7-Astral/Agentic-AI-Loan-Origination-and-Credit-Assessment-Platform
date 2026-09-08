import { redirect } from "next/navigation";

// Single-tenant dev convenience: the only seeded bank today is demo-mutual. Once multiple
// banks exist, this should become a bank picker rather than a fixed redirect.
export default function RootPage() {
  redirect("/demo-mutual");
}
